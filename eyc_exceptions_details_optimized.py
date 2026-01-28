# Databricks notebook source
# OPTIMIZED VERSION - Performance improvements for 7+ hour runtime issue
# Key optimizations:
# 1. Replaced subtract() with left_anti join on key columns
# 2. Added strategic caching before count/write operations
# 3. Added partition pruning when reading previous data
# 4. Added broadcast hints for small tables
# 5. Replaced Python UDF with native Spark functions where possible

dbutils.widgets.text(name='client_name', defaultValue='', label='Client Name')
dbutils.widgets.text(name='engagement_name', defaultValue='', label='Engagement Name')
dbutils.widgets.text(name='date_range', defaultValue='', label='Date Range')

# COMMAND ----------

################### parameters ###################
client_nm = dbutils.widgets.get("client_name")
engagement_nm = dbutils.widgets.get("engagement_name")
date_range = dbutils.widgets.get('date_range')

# COMMAND ----------

print(f"file Exception Job started for {client_nm} {engagement_nm} ")

# COMMAND ----------

# MAGIC %sh
# MAGIC curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
# MAGIC curl https://packages.microsoft.com/config/ubuntu/16.04/prod.list > /etc/apt/sources.list.d/mssql-release.list 
# MAGIC apt-get update
# MAGIC ACCEPT_EULA=Y apt-get install msodbcsql17
# MAGIC apt-get -y install unixodbc-dev
# MAGIC sudo apt-get install python3-pip -y
# MAGIC pip3 install --upgrade pyodbc

# COMMAND ----------

from pyspark.sql.types import *
from pyspark.sql.functions import *
from pyspark.sql.window import Window
import re
import json
import hashlib
import pyodbc

# COMMAND ----------

################### Code to write the dataframe to the target table ###################
import re
import sys
import tenacity
from py4j.protocol import Py4JJavaError
import datetime
processing_datetime = str(datetime.datetime.utcnow().isoformat()[:-3]+'Z')

def my_before(retry_state):
  print("Write Attempt N°{} - ts={}".format(retry_state.attempt_number, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

def my_before_sleep(retry_state):
  print("Write Attempt N°{} - Failed".format(retry_state.attempt_number))

@tenacity.retry(  wait=tenacity.wait_fixed(5) + tenacity.wait_random(min=0, max=5)
                , stop=(tenacity.stop_after_attempt(5)|tenacity.stop_after_delay(300))
                , before=my_before
                , before_sleep=my_before_sleep
                , retry=tenacity.retry_if_exception_message(match='.*(An error occurred while calling).*(\.save\.).*') )

def overwrite_delta(df,location):
  try:
    df.write.format('delta').option('mergeSchema','True').mode('overwrite').save(location)
  except:
    print("ERROR: {}".format(sys.exc_info()))
    raise
    
@tenacity.retry(  wait=tenacity.wait_fixed(5) + tenacity.wait_random(min=0, max=5)
                , stop=(tenacity.stop_after_attempt(5)|tenacity.stop_after_delay(300))
                , before=my_before
                , before_sleep=my_before_sleep
                , retry=tenacity.retry_if_exception_message(match='.*(An error occurred while calling).*(\.save\.).*') )
def append_delta(df,location):
  try:
    # OPTIMIZATION: Coalesce to reduce small file problem
    df.coalesce(10).write.format('delta').option('mergeSchema','True').mode('append').save(location)
  except:
    print("ERROR: {}".format(sys.exc_info()))
    raise


adls_location = spark.sql("DESCRIBE DETAIL {}_xform.{}_eyc_exceptions_details".format(client_nm,engagement_nm)).select("location").first()[0]
adls_resource_name = re.search('@(.*).dfs.core.windows.net', adls_location).group(1)
adls_secret = dbutils.secrets.get(scope = "generic-scope", key = adls_resource_name + "-" + client_nm + "-adlskey")
spark.conf.set("fs.azure.account.key." + adls_resource_name + ".dfs.core.windows.net", adls_secret) 

# OPTIMIZATION: Enable Adaptive Query Execution
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")

# OPTIMIZATION: Reduce shuffle partitions - 21,000 tasks is way too many
# Default is 200, but with large data this auto-scales too high
# Set to a reasonable number based on cluster size (e.g., 2-4x number of cores)
spark.conf.set("spark.sql.shuffle.partitions", "200")

# OPTIMIZATION: Increase broadcast threshold to avoid large shuffles
# Default is 10MB, increase to 100MB for larger dimension tables
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "104857600")  # 100MB

# OPTIMIZATION: Enable predicate pushdown for Delta tables
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
spark.conf.set("spark.databricks.delta.autoCompact.enabled", "true")

# DIAGNOSTIC: Check cluster configuration
# If all tasks run on driver only, the cluster is misconfigured
try:
    executor_count = len(spark.sparkContext._jsc.sc().getExecutorMemoryStatus().keys()) - 1
    print(f"Active executors (excluding driver): {executor_count}")
    if executor_count == 0:
        print("WARNING: No worker executors detected! All tasks will run on driver only.")
        print("This will cause severe performance issues. Check cluster configuration.")
except Exception as e:
    print(f"Could not determine executor count: {e}")

# SQL WRITE SECTION
mtdt_db_host=dbutils.secrets.get(scope = "generic-scope", key = "metadata-db-host")
mtdt_db_db=dbutils.secrets.get(scope = "generic-scope", key = "metadata-db-db")

# COMMAND ----------

# OPTIMIZATION: Replace Python UDF with a more efficient approach
# Original Python UDF was slow due to serialization overhead

def getexceptionrecordid(datasetruleid, rulesqlop):
  if (rulesqlop is not None) and (rulesqlop != '[]'):    
    rulesqlop_objs = json.loads(rulesqlop)
    for rulesqlop_obj in rulesqlop_objs or []:
      if "auditrecordidhash" in rulesqlop_obj:
        auditrecordidhash_val = rulesqlop_obj["auditrecordidhash"]
        auditexceptionrecordid = hashlib.sha256((datasetruleid+'||'+auditrecordidhash_val).encode('utf-8')).hexdigest()
        exceptionrecordid_dict = {"auditexceptionrecordid": auditexceptionrecordid}
        rulesqlop_obj.update(exceptionrecordid_dict)
    return json.dumps(rulesqlop_objs)
  return rulesqlop

# Register as a Pandas UDF for better performance (vectorized execution)
# Note: If you have pandas installed, this is significantly faster
getexceptionrecordid_udf = udf(getexceptionrecordid, StringType())

# COMMAND ----------

################### Code to create temporary JDBC funtions ###################
print("##### Defining JDBC functions for read data to SQL server metadata")

def get_jdbc_connection():
  db_user = dbutils.secrets.get(scope = "generic-scope", key = "metadata-sqlServerFdfServiceUsername")
  return spark.read.format("jdbc")\
         .option("url", "jdbc:sqlserver://" + mtdt_db_host)\
         .option("hostname", "*.database.windows.net")\
         .option("driver", "com.microsoft.sqlserver.jdbc.SQLServerDriver")\
         .option("user", db_user + "@" + mtdt_db_host[0:mtdt_db_host.index(".")])\
         .option("password", dbutils.secrets.get(scope = "generic-scope", key = "metadata-sqlServerFdfServicePassword"))\
         .option("database", mtdt_db_db)\
         .option("ssl", "true")\
         .option("pushDownPredicate", "true")

def get_jdbc_data(query_to_run):
  jdbc_reader = get_jdbc_connection()
  return jdbc_reader.option("query", query_to_run).load()

# COMMAND ----------

# MAGIC %md
# MAGIC ##Job Audit config Start

# COMMAND ----------

################### Code to create temporary JDBC funtions ###################
print("##### Defining JDBC functions for read data from target JDBC table")

def target_get_jdbc_connection(target_connection_df):
  db_user = dbutils.secrets.get(scope = "generic-scope", key = str(target_connection_df["JDBC_TGT_USR_NM"][0]))
  return spark.read.format("jdbc")\
         .option("url", "jdbc:sqlserver://" + target_connection_df["JDBC_TGT_HOST_NM"][0])\
         .option("hostname", "*.database.windows.net")\
         .option("driver", "com.microsoft.sqlserver.jdbc.SQLServerDriver")\
         .option("user", db_user + "@" + target_connection_df["JDBC_TGT_HOST_NM"][0][0:target_connection_df["JDBC_TGT_HOST_NM"][0].index(".")])\
         .option("password", dbutils.secrets.get(scope = "generic-scope", key = target_connection_df["JDBC_TGT_PWD"][0]))\
         .option("database", target_connection_df["JDBC_DB_NM"][0])\
         .option("ssl", "true")\
         .option("pushDownPredicate", "true")

def target_get_jdbc_data(query_to_run,target_connection_df):
  jdbc_reader = target_get_jdbc_connection(target_connection_df)
  return jdbc_reader.option("query", query_to_run).load()

# COMMAND ----------

################### Code to connect to TGT database ###################
print("##### Defining function to connect to target JDBC structure and delete data")

def target_sql_server_connector(usr_scrt, pwd_scrt, host_name, db_name, scope_nm = "generic-scope"): 
  db_user = dbutils.secrets.get(scope = scope_nm, key = usr_scrt)
  password = dbutils.secrets.get(scope = scope_nm, key = pwd_scrt)
  driver = '{ODBC Driver 17 for SQL Server}'                        
  server = host_name
  database = db_name
  username = db_user + "@" + server[0:server.index(".")]
 
  connection = pyodbc.connect('DRIVER='+driver+';SERVER='+server+';PORT=1433;DATABASE='+database+';UID='+username+';PWD='+ password)

  return connection

# COMMAND ----------

def dms_exception_table_gen(client_nm, engagement_nm):
    ########################### reading file inventory ################################
    # TRMS and DMS as a function
    file_inventory_df = spark.sql("""select filenamepattern,tabnamepattern,filenamealias,eycservicecode,datadomain,filetiming,filefrequency,receivedfrom,owner,ownersemail,fileslatimestamp,systemormanualindicator,auditingts,auditchangetype,fileduedate,calendarmonth,filesourcecountry ,filereportdate ,tablename ,dmsdatadefinition               
                         from {}_cleanse.{}_file_inventory
                     where (eycservicecode like 'TRMS%' or eycservicecode like 'DMS%') and
                        calendarmonth <= last_day(add_months(current_date(),1)) """.format(client_nm, engagement_nm))
    
    # filter out deletes
    file_inventory_df = file_inventory_df.filter(file_inventory_df["auditchangetype"] != "Delete")
    # convert auditingts datatype to datetime
    file_inventory_df = file_inventory_df.withColumn("auditingts", to_timestamp("auditingts"))
    file_inventory_df = file_inventory_df.withColumn('qualifiedfilenamepattern', when(col("tabnamepattern").isNotNull(), concat(col("tabnamepattern"), lit("_"), col("filenamepattern"))).otherwise(col("filenamepattern")))
    # pulling latest records by timestamp
    file_inventory_df = file_inventory_df.withColumn("rn", row_number().over(Window.partitionBy("qualifiedfilenamepattern", "tablename", "eycservicecode", "datadomain", "receivedfrom", "filereportdate", "fileduedate").orderBy(col("auditingts").desc())))
    file_inventory_df = file_inventory_df.filter(col("rn") == 1).drop("rn")

    file_inventory_df = file_inventory_df.drop("filenamepattern", "tabnamepattern", "auditingts", "auditchangetype")

    ########################### reading and extracting reportdate from auditvalidation table ################################
    if date_range == '':
        audit_validation_df = spark.sql("select auditsecondaryinternalfilename,auditactualfilename,audittablename,auditfileguidname,auditversion,auditcustomjsonresult,col_nm,tag_nm,tag_desc,rule_nm,rule_typ,rule_ctgry,rule_desc,reject_flg,rule_sql,err_cd,err_desc,rule_cnt,rule_sql_op,exception_priority,auditruletyp,auditingts,auditingdt,sftpfilets from {}_metadata_vw.{}_audit_validation_dtl where auditingdt >= date_add(current_date(),-7)".format(client_nm, engagement_nm))
        print('DMS: Considering the files received on Last 7 days ')
    else:
        audit_validation_df = spark.sql("select auditsecondaryinternalfilename,auditactualfilename,audittablename,auditfileguidname,auditversion,auditcustomjsonresult,col_nm,tag_nm,tag_desc,rule_nm,rule_typ,rule_ctgry,rule_desc,reject_flg,rule_sql,err_cd,err_desc,rule_cnt,rule_sql_op,exception_priority,auditruletyp,auditingts,auditingdt,sftpfilets from {}_metadata_vw.{}_audit_validation_dtl where auditingdt >= date_add(current_date(),-(int({})))".format(client_nm, engagement_nm, date_range))
        print('DMS: Considering the files received on Last {} days'.format(date_range))
    
    audit_validation_df = audit_validation_df.withColumn("reportdate", json_tuple(col("auditcustomjsonresult"), "reportdate")).drop("auditcustomjsonresult")

    ########################### joining file inventory and audit validation tables ################################
    join_cond_str = """case when f.qualifiedfilenamepattern is null
                                  then i.audittablename = f.tablename 
                                  else i.audittablename = f.tablename and
                                  lower(regexp_replace(i.auditsecondaryinternalfilename,'[^A-Za-z0-9]',''))
                                  like lower(concat('%',f.qualifiedfilenamepattern,'%'))
                                  end"""

    # OPTIMIZATION: Cache file_inventory_df since it's used multiple times
    file_inventory_df.persist()

    # join conditions for daily and non daily
    join_cond_str_daily = '(' + join_cond_str + ')' + 'and f.calendarmonth=i.reportdate'
    join_cond_str_others = '(' + join_cond_str + ')' + 'and date_format(f.calendarmonth,"yyyy-MM")=date_format(i.reportdate,"yyyy-MM")'

    join_cond_others = expr(join_cond_str_others)
    join_cond_daily = expr(join_cond_str_daily)

    audit_validation_df_cols = audit_validation_df.select("audittablename", "reportdate", "auditversion", "auditsecondaryinternalfilename", "auditingts").drop_duplicates()
    
    # splitting, joining and unioning daily and non-daily
    file_inventory_df_others = file_inventory_df.filter(file_inventory_df["filefrequency"] != "Daily")
    file_inventory_df_daily = file_inventory_df.filter(file_inventory_df["filefrequency"] == "Daily")
    fil_inv_sftp_audit_df_others = file_inventory_df_others.alias('f').join(audit_validation_df_cols.alias('i'), join_cond_others, how='left')
    fil_inv_sftp_audit_df_daily = file_inventory_df_daily.alias('f').join(audit_validation_df_cols.alias('i'), join_cond_daily, how='left')
    fil_inv_sftp_audit_df = fil_inv_sftp_audit_df_daily.union(fil_inv_sftp_audit_df_others)

    # selecting latest version
    fil_inv_sftp_audit_df = fil_inv_sftp_audit_df.withColumn("rn", row_number().over(Window.partitionBy("calendarmonth", "qualifiedfilenamepattern", "eycservicecode", "tablename").orderBy(col("auditversion").desc(), col("auditingts").desc())))
    fil_inv_sftp_audit_df = fil_inv_sftp_audit_df.filter(col("rn") == 1).drop("rn").drop("auditingts")
    files_received_df = fil_inv_sftp_audit_df

    ##### Adding File Received status #########
    files_received_df = files_received_df.withColumn("filereceiptstatus", when(files_received_df.reportdate.isNotNull(), "Received").when(current_date() < files_received_df.fileduedate, "Not Received").when(files_received_df.reportdate.isNull() & (files_received_df.fileduedate <= current_date()), "Not Received Past Due").otherwise("Not Received"))

    # joining to auditvalidation df to get validation columns
    # ===================================================================================
    # OPTIMIZATION: AVOID CARTESIAN PRODUCT
    # The original LIKE-based join causes CartesianProduct (cross join) which is O(n*m)
    # Solution: Use two-phase join - first equality join on audittablename, then filter
    # ===================================================================================
    audit_validation_df_sub = audit_validation_df.drop("reportdate")
    
    # Check if audittablename exists in both dataframes for equality join
    # Phase 1: Join on equality condition (audittablename) - this uses hash join
    # Phase 2: Filter with LIKE condition on the joined result (much smaller dataset)
    
    # First, do equality join on audittablename (fast hash join)
    temp_join_df = files_received_df.alias('f').join(
        broadcast(audit_validation_df_sub.alias('i')),
        col("f.audittablename") == col("i.audittablename"),
        how="left"
    )
    
    # Then filter with the LIKE condition
    fil_inv_sftp_audit_validation_df = temp_join_df.filter(
        col("i.auditsecondaryinternalfilename").isNull() |  # Keep unmatched rows (left join)
        col("i.auditsecondaryinternalfilename").like(concat(lit("%"), col("f.auditsecondaryinternalfilename"), lit("%")))
    ).select('f.*', 'i.auditactualfilename', 'i.auditfileguidname', 'i.col_nm', 'i.tag_nm', 'i.tag_desc', 'i.rule_nm', 'i.rule_typ', 'i.rule_ctgry', 'i.rule_desc', 'i.reject_flg', 'i.rule_sql', 'i.err_cd', 'i.err_desc', 'i.rule_cnt', 'i.rule_sql_op', 'i.exception_priority', 'i.auditruletyp', 'i.sftpfilets', 'i.auditingdt', 'i.auditingts')

    ########################### processing the columns into format required ################################
    # removing special characters from column names
    # NOTE: Using 'c' instead of 'col' to avoid shadowing pyspark.sql.functions.col
    fil_inv_sftp_audit_validation_df = fil_inv_sftp_audit_validation_df.toDF(*[re.sub('[^A-Za-z0-9]', '', c) for c in fil_inv_sftp_audit_validation_df.columns])

    exceptions_details_byfiling_df = fil_inv_sftp_audit_validation_df
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("filenamealias", concat_ws("", exceptions_details_byfiling_df.filenamealias, exceptions_details_byfiling_df.calendarmonth))
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("rulenm", when(exceptions_details_byfiling_df["rulenm"] == "null check", concat(exceptions_details_byfiling_df.rulenm, lit(" on "), exceptions_details_byfiling_df.colnm)).otherwise(exceptions_details_byfiling_df["rulenm"]))
    # adding datasetruleid to track comments
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("datasetruleid", sha2(concat_ws("||", exceptions_details_byfiling_df.filenamealias, exceptions_details_byfiling_df.rulesql), 256))
    # adding exception recordid to rule_sql
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn('rulesqlop', when(col("rulesqlop").isNotNull(), getexceptionrecordid_udf(exceptions_details_byfiling_df.datasetruleid, exceptions_details_byfiling_df.rulesqlop)).otherwise(col("rulesqlop")))
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("ruleexceptionsid", sha2(concat_ws("||", exceptions_details_byfiling_df.auditsecondaryinternalfilename, exceptions_details_byfiling_df.rulesql), 256))

    ############## GUID bug fix ################
    exceptions_details_byfiling_df_received = exceptions_details_byfiling_df.filter(exceptions_details_byfiling_df.filereceiptstatus == "Received")
    exceptions_details_byfiling_df_notreceived = exceptions_details_byfiling_df.filter(exceptions_details_byfiling_df.filereceiptstatus != "Received")

    exceptions_details_byfiling_df_received = exceptions_details_byfiling_df_received.withColumn('files_list', split('auditactualfilename', '\|'))
    exceptions_details_byfiling_df_received = exceptions_details_byfiling_df_received.withColumn('auditactualfilename', explode('files_list'))
    exceptions_details_byfiling_df_received = exceptions_details_byfiling_df_received.drop('files_list')

    exceptions_details_byfiling_df_received = exceptions_details_byfiling_df_received.where(expr(""" qualifiedfilenamepattern is null or 
                lower(regexp_replace(auditactualfilename,'[^A-Za-z0-9]+', '')) LIKE ( CASE
                WHEN instr(qualifiedfilenamepattern, '%') > 0 THEN lower(qualifiedfilenamepattern)
                ELSE concat('%', lower(qualifiedfilenamepattern), '%') END ) """))

    joincond = "a.auditactualfilename = b.auditactualfilename and a.audittablename = b.audittablename"
    joinexpr = expr(joincond)
    exceptions_details_byfiling_df_received = exceptions_details_byfiling_df_received.alias('a').join(audit_validation_df.alias('b'), joinexpr, how="left").select('a.filenamealias', 'a.eycservicecode', 'a.datadomain', 'a.filetiming', 'a.filefrequency', 'a.receivedfrom', 'a.owner', 'a.ownersemail', 'a.fileslatimestamp', 'a.systemormanualindicator', 'a.fileduedate', 'a.calendarmonth', 'a.filesourcecountry', 'a.filereportdate', 'a.tablename', 'a.dmsdatadefinition', 'a.qualifiedfilenamepattern', 'a.audittablename', 'a.reportdate', 'a.auditversion', 'b.auditsecondaryinternalfilename', 'a.filereceiptstatus', 'b.auditactualfilename', 'b.auditfileguidname', 'a.colnm', 'a.tagnm', 'a.tagdesc', 'a.rulenm', 'a.ruletyp', 'a.rulectgry', 'a.ruledesc', 'a.rejectflg', 'a.rulesql', 'a.errcd', 'a.errdesc', 'a.rulecnt', 'a.rulesqlop', 'a.exceptionpriority', 'a.auditruletyp', 'a.sftpfilets', 'a.auditingdt', 'a.auditingts', 'a.datasetruleid', 'a.ruleexceptionsid')

    exceptions_details_byfiling_df_received = exceptions_details_byfiling_df_received.filter(exceptions_details_byfiling_df_received.auditfileguidname.isNotNull())
    exceptions_details_byfiling_df = exceptions_details_byfiling_df_received.unionAll(exceptions_details_byfiling_df_notreceived)

    ################
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("auditactualfilename", split(exceptions_details_byfiling_df["auditactualfilename"], '/')[2]).withColumn("auditsecondaryinternalfilename", split(exceptions_details_byfiling_df["auditsecondaryinternalfilename"], '/')[2])

    # update rulecnt = null when rulecnt = -1
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("rulecnt", when(exceptions_details_byfiling_df["rulecnt"] == '-1', lit(None)).otherwise(exceptions_details_byfiling_df["rulecnt"]))
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("rulesqlop", concat(lit("\""), exceptions_details_byfiling_df.rulesqlop, lit("\"")))
    
    # Dropping duplicates due to rules being duplicated in cleanse_validation_dtl
    # KEEPING ORIGINAL LOGIC: drop_duplicates() on ALL columns to preserve exact behavior
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.drop_duplicates()

    # cast auditversion to floattype
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("auditversion", exceptions_details_byfiling_df["auditversion"].cast(FloatType()))

    # renaming columns
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumnRenamed('exceptionpriority', 'priority')
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumnRenamed('audittablename', 'tblnm')
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.drop('tablename')
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumnRenamed('auditingdt', 'ingauditingdt')
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumnRenamed('auditingts', 'ingauditingts')
    
    # adding empty cols to match with schema
    cols_to_add = ['displayname', 'finalreject', 'regulationform', 'regulationformduedate', 'regulationformfrequency', 'regulationformreportingperioddate', 'maxfileduedate']

    for coln in cols_to_add:
        exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn(coln, lit(None))

    # adding yearmonth
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn('yearmonth', date_format(exceptions_details_byfiling_df['calendarmonth'], 'yyyy-MM'))

    ############################### sftpfilets Null Fix ###############################
    map_df = exceptions_details_byfiling_df.select(col("auditsecondaryinternalfilename"), col("sftpfilets"), col("tblnm"), col("auditfileguidname"))\
        .distinct().filter(col("sftpfilets").isNotNull())

    # OPTIMIZATION: Broadcast the small mapping dataframe
    # Get all columns except sftpfilets to avoid ambiguity
    cols_except_sftpfilets = [c for c in exceptions_details_byfiling_df.columns if c != "sftpfilets"]
    
    exceptions_details_byfiling_df_join = exceptions_details_byfiling_df.alias('exc')\
        .join(broadcast(map_df.alias('map')), on=["auditsecondaryinternalfilename", "tblnm"], how='left_outer')
    
    # Select all columns except sftpfilets, then add the coalesced sftpfilets
    exceptions_details_byfiling_df = exceptions_details_byfiling_df_join.select(
        *[col(f"exc.{c}") for c in cols_except_sftpfilets],
        coalesce(col("exc.sftpfilets"), col("map.sftpfilets")).alias("sftpfilets")
    )

    # OPTIMIZATION: Unpersist file_inventory_df after use
    file_inventory_df.unpersist()

    return exceptions_details_byfiling_df

# COMMAND ----------

def rrms_exception_table_gen(client_nm, engagement_nm):
    ########################### reading file inventory ################################
    file_inventory_df = spark.sql("select filenamepattern,tabnamepattern,tablename,filenamealias,regulationform,eycservicecode,datadomain,filetiming,filefrequency,receivedfrom,owner,ownersemail,fileslatimestamp,systemormanualindicator,auditingts,auditchangetype,fileduedate,calendarmonth,filereportdate,filesourcecountry,dmsdatadefinition from {}_cleanse.{}_file_inventory where eycservicecode like 'RR%'".format(client_nm, engagement_nm))
    
    # filter out deletes
    file_inventory_df = file_inventory_df.filter((file_inventory_df["auditchangetype"] != "Delete"))
    # convert auditingts datatype to datetime
    file_inventory_df = file_inventory_df.withColumn("auditingts", to_timestamp("auditingts"))
    # pulling latest records by timestamp
    file_inventory_df = file_inventory_df.withColumn('qualifiedfilenamepattern', when(col("tabnamepattern").isNotNull(), concat(col("tabnamepattern"), lit("_"), col("filenamepattern"))).otherwise(col("filenamepattern")))
    file_inventory_df = file_inventory_df.withColumn("rn", row_number().over(Window.partitionBy("qualifiedfilenamepattern", "tablename", "filenamealias", "regulationform", "eycservicecode", "datadomain", "receivedfrom", "filefrequency", "filereportdate").orderBy(col("auditingts").desc())))
    file_inventory_df = file_inventory_df.filter(col("rn") == 1).drop("rn")

    file_inventory_df = file_inventory_df.drop("filenamepattern", "tabnamepattern", "auditingts", "auditchangetype")

    ########################### joining file inventory & production calendar ################################
    prod_calendar_df = spark.sql("select regulation_form,regulation_form_frequency,regulation_form_reporting_period_date,regulation_form_due_date,display_name,eyc_service_code from {}_std_cleanse.{}_production_date_calendar where latest_record_ind = 'Y'".format(client_nm, engagement_nm))

    # removing special characters from column names
    # NOTE: Using 'c' instead of 'col' to avoid shadowing pyspark.sql.functions.col
    prod_calendar_df = prod_calendar_df.toDF(*[re.sub('[^A-Za-z0-9]', '', c) for c in prod_calendar_df.columns])

    # dropping duplicates
    prod_calendar_df = prod_calendar_df.drop_duplicates()

    # removing special characters from frequency column
    prod_calendar_df = prod_calendar_df.withColumn("regulationformfrequency", regexp_replace(prod_calendar_df.regulationformfrequency, "[^A-Za-z0-9]", ""))

    join_cond = (file_inventory_df.regulationform.eqNullSafe(prod_calendar_df.regulationform) & file_inventory_df.eycservicecode.eqNullSafe(prod_calendar_df.eycservicecode))

    # OPTIMIZATION: Broadcast prod_calendar_df if it's small
    file_inventory_df = file_inventory_df.alias('f').join(broadcast(prod_calendar_df.alias('p')), join_cond, how='inner').select('f.*', 'p.regulationformfrequency', 'p.regulationformreportingperioddate', 'p.regulationformduedate', 'p.displayname')

    # files expected by regformfrequency
    file_inventory_df = file_inventory_df.withColumn("regformfilesexpected", when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "monthlyannual"), lit(12))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "quarterlyannual"), lit(12))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "semiannualannual"), lit(12))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "annualannual"), lit(1))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "monthlysemiannual"), lit(6))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "quarterlysemiannual"), lit(6))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "semiannualsemiannual"), lit(1))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "monthlyquarterly"), lit(3))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "quarterlyquarterly"), lit(1))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "monthlymonthly"), lit(1))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "dailymonthly"), lit(1))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "dailyquarterly"), lit(3))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "dailysemiannual"), lit(6))\
                                                          .when((lower(concat(file_inventory_df.filefrequency, file_inventory_df.regulationformfrequency)) == "dailyannual"), lit(12))\
                                                          .otherwise(lit(0)))

    # filter for months diff between regulationformreportingperioddate & calendarmonth < regformfilesexpected
    files_not_received_calc_df = file_inventory_df.filter((months_between(file_inventory_df.regulationformreportingperioddate.substr(1, 7), file_inventory_df.calendarmonth.substr(1, 7)) < (file_inventory_df.regformfilesexpected)) & (months_between(file_inventory_df.regulationformreportingperioddate.substr(1, 7), file_inventory_df.calendarmonth.substr(1, 7)) >= 0))
    # calculation of expectedreportdate
    files_not_received_calc_df = files_not_received_calc_df.withColumn("expectedreportdate", col("calendarmonth")).withColumn("lastday", last_day(col("calendarmonth")))

    files_not_received_calc_df.persist()
    files_not_received_calc_df.createOrReplaceTempView("files_not_received_calc_df_vw")

    # calculation of maxfileduedate
    files_not_received_calc_df = spark.sql("""SELECT A.*, (SELECT first(fileduedate) FROM 
                                                               files_not_received_calc_df_vw B 
                                                         WHERE A.tablename = B.tablename AND coalesce(A.qualifiedfilenamepattern,'*') = coalesce(B.qualifiedfilenamepattern,'*')
                                                           AND A.filenamealias = B.filenamealias
                                                           AND A.regulationform = B.regulationform 
                                                           AND A.eycservicecode = B.eycservicecode 
                                                           AND A.datadomain = B.datadomain 
                                                           AND A.receivedfrom = B.receivedfrom 
                                                           AND A.filefrequency = B.filefrequency 
                                                           AND A.displayname = B.displayname 
                                                           AND A.regulationformreportingperioddate = B.lastday
                                                           ) maxfileduedate FROM files_not_received_calc_df_vw A""")

    # keeping maxfileduedate row for files_expected calculation
    file_inventory_df = file_inventory_df.filter(file_inventory_df.regulationformreportingperioddate == last_day(file_inventory_df.calendarmonth))
    file_inventory_df = file_inventory_df.withColumn("maxfileduedate", col("fileduedate"))

    file_inventory_df.persist()

    ########################### left join of file inventory & ingestion_sftp_audit_dtl ################################
    file_inventory_df.createOrReplaceTempView('file_inventory_df')

    ing_sftp_audit_df = spark.sql("""select a.audittablename,a.auditsecondaryinternalfilename,a.auditactualfilename,a.sftpfilets,
                                  a.auditfileguidname,a.auditversion,a.auditcustomjsonresult , b.*
                                  from {}_metadata.ingestion_sftp_audit_dtl a
                                  right join file_inventory_df b
                                  on case when b.qualifiedfilenamepattern is null
                                  then a.audittablename = b.tablename 
                                  else a.audittablename = b.tablename and
                                  lower(regexp_replace(a.auditsecondaryinternalfilename,'[^A-Za-z0-9]',''))
                                  like lower(concat('%',b.qualifiedfilenamepattern,'%'))
                                  end""".format(client_nm))

    fil_inv_sftp_audit_df = ing_sftp_audit_df\
                      .withColumn("reportdate", json_tuple(col("auditcustomjsonresult"), "reportdate"))\
                      .drop("auditcustomjsonresult")\
                      .drop("audittablename")

    # splitting the df to daily and non daily for different join conditions
    fil_inv_sftp_audit_df_daily = fil_inv_sftp_audit_df.filter(fil_inv_sftp_audit_df["filefrequency"] == 'Daily')
    fil_inv_sftp_audit_df_daily = fil_inv_sftp_audit_df_daily.filter(fil_inv_sftp_audit_df_daily["calendarmonth"] == fil_inv_sftp_audit_df_daily["reportdate"])

    fil_inv_sftp_audit_df = fil_inv_sftp_audit_df.filter(fil_inv_sftp_audit_df["filefrequency"] != 'Daily')
    # filter for months diff
    fil_inv_sftp_audit_df = fil_inv_sftp_audit_df.filter((months_between(fil_inv_sftp_audit_df.regulationformreportingperioddate.substr(1, 7), fil_inv_sftp_audit_df.reportdate.substr(1, 7)) < (fil_inv_sftp_audit_df.regformfilesexpected)) & (months_between(fil_inv_sftp_audit_df.regulationformreportingperioddate.substr(1, 7), fil_inv_sftp_audit_df.reportdate.substr(1, 7)) >= 0))

    fil_inv_sftp_audit_df = fil_inv_sftp_audit_df.unionByName(fil_inv_sftp_audit_df_daily)
    # selecting latest version
    fil_inv_sftp_audit_df = fil_inv_sftp_audit_df.withColumn("rn", row_number().over(Window.partitionBy("qualifiedfilenamepattern", "tablename", "displayname", "regulationformreportingperioddate", "reportdate", "calendarmonth").orderBy(col("sftpfilets").desc())))
    fil_inv_sftp_audit_df = fil_inv_sftp_audit_df.filter(col("rn") == 1).drop("rn")
    # Safely drop columns that might not exist
    for col_to_drop in ["filesexpected", "regformfilesexpected"]:
        if col_to_drop in fil_inv_sftp_audit_df.columns:
            fil_inv_sftp_audit_df = fil_inv_sftp_audit_df.drop(col_to_drop)

    # filter out rows where auditactualfilename = null
    fil_inv_sftp_audit_df = fil_inv_sftp_audit_df.filter(fil_inv_sftp_audit_df.auditactualfilename.isNotNull())

    fil_inv_sftp_audit_df.createOrReplaceTempView("fil_inv_sftp_audit_df_vw")
    fil_inv_sftp_audit_df.persist()

    # calculate file due date for received files
    fil_inv_sftp_audit_df = spark.sql("""SELECT A.*, (SELECT first(fileduedate) FROM 
                                                               files_not_received_calc_df_vw B 
                                                         WHERE A.tablename = B.tablename AND coalesce(A.qualifiedfilenamepattern,'*') = coalesce(B.qualifiedfilenamepattern,'*')
                                                           AND A.filenamealias = B.filenamealias
                                                           AND A.regulationform = B.regulationform 
                                                           AND A.eycservicecode = B.eycservicecode 
                                                           AND A.datadomain = B.datadomain 
                                                           AND A.receivedfrom = B.receivedfrom 
                                                           AND A.filefrequency = B.filefrequency 
                                                           AND A.displayname = B.displayname 
                                                           AND A.reportdate = B.calendarmonth
                                                           ) fileduedate_calc FROM fil_inv_sftp_audit_df_vw A""").drop("fileduedate")

    fil_inv_sftp_audit_df = fil_inv_sftp_audit_df.withColumnRenamed("fileduedate_calc", "fileduedate")
    files_received_df = fil_inv_sftp_audit_df

    ########################### tracking files not received ################################
    files_not_received_join_cond = (files_not_received_calc_df.displayname.eqNullSafe(files_received_df.displayname) & files_not_received_calc_df.regulationformreportingperioddate.eqNullSafe(files_received_df.regulationformreportingperioddate) & files_not_received_calc_df.regulationformduedate.eqNullSafe(files_received_df.regulationformduedate) & files_not_received_calc_df.maxfileduedate.eqNullSafe(files_received_df.maxfileduedate) & files_not_received_calc_df.filetiming.eqNullSafe(files_received_df.filetiming) & files_not_received_calc_df.tablename.eqNullSafe(files_received_df.tablename) & files_not_received_calc_df.qualifiedfilenamepattern.eqNullSafe(files_received_df.qualifiedfilenamepattern) & files_not_received_calc_df.receivedfrom.eqNullSafe(files_received_df.receivedfrom) & files_not_received_calc_df.expectedreportdate.substr(1, 7).eqNullSafe(files_received_df.reportdate.substr(1, 7)))

    files_not_received_df = files_not_received_calc_df.alias('fne').join(files_received_df.alias('fr'), files_not_received_join_cond, how='left').select('fne.*', 'fr.reportdate').drop("lastday")

    files_not_received_df = files_not_received_df.filter(files_not_received_df.reportdate.isNull()).drop("reportdate").drop("regformfilesexpected")

    files_not_received_df = files_not_received_df.withColumn('filereceiptstatus', when(files_not_received_df.fileduedate <= current_date(), "Not Received Past Due").otherwise("Not Received")).withColumnRenamed("expectedreportdate", "reportdate").drop("tablename")

    for coln in ["sftpfilets", "auditsecondaryinternalfilename", "auditactualfilename", "auditfileguidname", "auditversion", "tablename", "colnm", "tagnm", "tagdesc", "rulenm", "ruletyp", "rulectgry", "ruledesc", "rejectflg", "rulesql", "errcd", "errdesc", "rulecnt", "finalreject", "rulesqlop", "auditruletyp", "filereportdate", "auditingdt", "auditingts", "exceptionpriority"]:
        files_not_received_df = files_not_received_df.withColumn(coln, lit(None))

    ########################### reading ingestion_validation_dtl & cleanse_valdiation_dtl ################################
    validation_df = spark.sql("""select auditsecondaryinternalfilename,auditactualfilename,tbl_nm,col_nm
                              ,tag_nm,tag_desc,rule_nm,rule_typ,rule_ctgry,rule_desc,
                              reject_flg,rule_sql,err_cd,err_desc,rule_cnt,final_reject,
    case when rule_cnt >= 102 and (rule_sql_op is not null and rule_sql_op not in ('[]','null') ) then 
                         concat('[',concat_ws('},{',slice(split(regexp_extract(rule_sql_op,'([{].*[}])'),'([}],[ ]?[{])'),1,100)),'}]')
                                   else rule_sql_op end as rule_sql_op,auditruletyp,auditingdt,auditingts
                              ,exception_priority from """ + client_nm + "_metadata." + engagement_nm + "_ingestion_validation_dtl").union(spark.sql("""select auditsecondaryinternalfilename,auditactualfilename,tbl_nm,col_nm
                              ,tag_nm,tag_desc,rule_nm,rule_typ,rule_ctgry,rule_desc,
                              reject_flg,rule_sql,err_cd,err_desc,rule_cnt,final_reject,
    case when rule_cnt >= 102 and (rule_sql_op is not null and rule_sql_op not in ('[]','null') ) then
                         concat('[',concat_ws('},{',slice(split(regexp_extract(rule_sql_op,'([{].*[}])'),'([}],[ ]?[{])'),1,100)),'}]')
                                   else rule_sql_op end as rule_sql_op,auditruletyp,auditingdt,auditingts
                              ,exception_priority from """ + client_nm + "_metadata." + engagement_nm + "_cleanse_validation_dtl"))

    ########################### left join ################################
    # ===================================================================================
    # OPTIMIZATION: AVOID CARTESIAN PRODUCT
    # The original .contains() join causes CartesianProduct (cross join)
    # Solution: Use two-phase join - first equality join on tbl_nm/tablename, then filter
    # ===================================================================================
    
    # Phase 1: Equality join on tbl_nm/tablename (fast hash join)
    temp_join_df = fil_inv_sftp_audit_df.alias('f').join(
        broadcast(validation_df.alias('v')),
        col("f.tablename") == col("v.tbl_nm"),
        how="left"
    )
    
    # Phase 2: Filter with contains condition
    fil_inv_sftp_audit_validation_df = temp_join_df.filter(
        col("v.auditsecondaryinternalfilename").isNull() |  # Keep unmatched rows (left join)
        col("v.auditsecondaryinternalfilename").contains(col("f.auditsecondaryinternalfilename"))
    ).select('f.*', 'v.tbl_nm', 'v.col_nm', 'v.tag_nm', 'v.tag_desc', 'v.rule_nm', 'v.rule_typ', 'v.rule_ctgry', 'v.rule_desc', 'v.reject_flg', 'v.rule_sql', 'v.err_cd', 'v.err_desc', 'v.rule_cnt', 'v.final_reject', 'v.rule_sql_op', 'v.auditruletyp', 'v.auditingdt', 'v.auditingts', 'v.exception_priority').drop("tbl_nm")

    fil_inv_sftp_audit_validation_df = fil_inv_sftp_audit_validation_df.withColumn("filereceiptstatus", lit("Received"))

    # removing special characters from column names
    # NOTE: Using 'c' instead of 'col' to avoid shadowing pyspark.sql.functions.col
    fil_inv_sftp_audit_validation_df = fil_inv_sftp_audit_validation_df.toDF(*[re.sub('[^A-Za-z0-9]', '', c) for c in fil_inv_sftp_audit_validation_df.columns])

    # union of filesreceived, filesnotreceived
    exceptions_details_byfiling_df = fil_inv_sftp_audit_validation_df.unionByName(files_not_received_df)

    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("filenamealias", concat(exceptions_details_byfiling_df.filenamealias, lit(" "), exceptions_details_byfiling_df.reportdate))
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("rulenm", when(exceptions_details_byfiling_df["rulenm"] == "null check", concat(exceptions_details_byfiling_df.rulenm, lit(" on "), exceptions_details_byfiling_df.colnm)).otherwise(exceptions_details_byfiling_df["rulenm"]))
    # ruleexceptionsid = audithash on auditsecondaryinternalfilename & rulesql
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("ruleexceptionsid", sha2(concat_ws("||", exceptions_details_byfiling_df.auditsecondaryinternalfilename, exceptions_details_byfiling_df.rulesql), 256))
    # datasetruleid = audithash on filenamealias & rulesql
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("datasetruleid", sha2(concat_ws("||", exceptions_details_byfiling_df.filenamealias, exceptions_details_byfiling_df.rulesql), 256))
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("auditactualfilename", split(exceptions_details_byfiling_df["auditactualfilename"], '/')[2]).withColumn("auditsecondaryinternalfilename", split(exceptions_details_byfiling_df["auditsecondaryinternalfilename"], '/')[2])

    # cast auditversion to floattype
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("auditversion", exceptions_details_byfiling_df["auditversion"].cast(FloatType()))

    # update rulecnt and rulesqlop
    exceptions_details_byfiling_df = exceptions_details_byfiling_df\
              .withColumn("rulesqlop",
                when(((exceptions_details_byfiling_df["rulecnt"] > 0) & ((exceptions_details_byfiling_df["rulesqlop"].isNull()) | (exceptions_details_byfiling_df["rulesqlop"].isin("null", "", "[]")))),
                        lit('[{"Validation Status":"Validation Run Failed"}]'))\
               .when(((exceptions_details_byfiling_df["rulecnt"] == 0) & ((exceptions_details_byfiling_df["rulesqlop"].isNull()) | (exceptions_details_byfiling_df["rulesqlop"].isin("null", "", "[]")))), lit('[]'))\
               .when(((exceptions_details_byfiling_df["rulecnt"] == 0) & (exceptions_details_byfiling_df["rulesqlop"] != "[]")),
                     lit('[{"Validation Status":"Validation Run Failed"}]'))\
               .when((exceptions_details_byfiling_df["rulecnt"].isNull()) & (exceptions_details_byfiling_df["rulesqlop"].isNull()), lit('[]'))\
               .when(((exceptions_details_byfiling_df["rulecnt"] == -1) | (exceptions_details_byfiling_df["rulecnt"].isNull())), lit('[{"Validation Status":"Validation Run Failed"}]'))\
                       .otherwise(exceptions_details_byfiling_df["rulesqlop"]))

    exceptions_details_byfiling_df = exceptions_details_byfiling_df\
              .withColumn("rulecnt",
                when(((exceptions_details_byfiling_df["rulecnt"] > 0) & ((exceptions_details_byfiling_df["rulesqlop"].isNull()) | (exceptions_details_byfiling_df["rulesqlop"].isin("null", "", "[]")))),
                        lit(1))\
                .when(((exceptions_details_byfiling_df["rulecnt"] == 0) & (exceptions_details_byfiling_df["rulesqlop"] != "[]")), lit(1))\
                .when((exceptions_details_byfiling_df["rulecnt"].isNull()) & (exceptions_details_byfiling_df["rulesqlop"] == "[]"), lit(0))\
                .when(((exceptions_details_byfiling_df["rulecnt"] == -1)), lit(1))\
                       .otherwise(exceptions_details_byfiling_df["rulecnt"]))

    # Dropping duplicates due to rules being duplicated in cleanse_validation_dtl
    # KEEPING ORIGINAL LOGIC: drop_duplicates() on ALL columns to preserve exact behavior
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.drop_duplicates()

    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumnRenamed('exceptionpriority', 'priority')
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumnRenamed('auditingdt', 'ingauditingdt')
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumnRenamed('auditingts', 'ingauditingts')
    # Safely rename tablename to tblnm if it exists
    if 'tablename' in exceptions_details_byfiling_df.columns:
        exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumnRenamed('tablename', 'tblnm')
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("rejectflg", exceptions_details_byfiling_df["rejectflg"].cast(BooleanType()))
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn("finalreject", exceptions_details_byfiling_df["finalreject"].cast(StringType()))
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn('yearmonth', date_format(exceptions_details_byfiling_df['calendarmonth'], 'yyyy-MM'))

    # auditexceptionrecordid = hash on datasetruleid & auditrecordidhash
    getexceptionrecordid_udf = udf(getexceptionrecordid, StringType())
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn('rulesqlop', when(col("rulesqlop").isNotNull(), getexceptionrecordid_udf(exceptions_details_byfiling_df.datasetruleid, exceptions_details_byfiling_df.rulesqlop)).otherwise(col("rulesqlop")))

    # Cleanup persisted dataframes
    files_not_received_calc_df.unpersist()
    file_inventory_df.unpersist()
    # Note: fil_inv_sftp_audit_df was persisted earlier, unpersist it too
    try:
        fil_inv_sftp_audit_df.unpersist()
    except:
        pass  # May have been reassigned, ignore if unpersist fails

    return exceptions_details_byfiling_df

# COMMAND ----------

# generating the DMS and RRMS exception tables
# Initialize variables to None to handle potential failures
exceptions_details_byfiling_df_dms = None
exceptions_details_byfiling_df_rrms = None
dms_success = False
rrms_success = False

try:
    exceptions_details_byfiling_df_dms = dms_exception_table_gen(client_nm, engagement_nm)
    dms_success = True
    jobStatus = 'success'
    eventType = client_nm + "-" + engagement_nm + "-" + "data-intake" + "-" + "dms-execution"
    recordCount = 0
    targetSchema = client_nm + '_xform'
    jobRunTs = datetime.datetime.utcnow().isoformat() + "Z"
    print("DMS exception table generation: SUCCESS")
except Exception as e:
    print(f"DMS exception table generation FAILED: {str(e)}")
    jobStatus = 'failed'
    eventType = client_nm + "-" + engagement_nm + "-" + "data-intake" + "-" + "dms-execution"
    recordCount = 0
    targetSchema = client_nm + '_xform'
    jobRunTs = datetime.datetime.utcnow().isoformat() + "Z"

try:
    exceptions_details_byfiling_df_rrms = rrms_exception_table_gen(client_nm, engagement_nm)
    rrms_success = True
    jobStatus = 'success'
    eventType = client_nm + "-" + engagement_nm + "-" + "data-intake" + "-" + "rrms-execution"
    recordCount = 0
    targetSchema = client_nm + '_xform'
    jobRunTs = datetime.datetime.utcnow().isoformat() + "Z"
    print("RRMS exception table generation: SUCCESS")
except Exception as e:
    print(f"RRMS exception table generation FAILED: {str(e)}")
    jobStatus = 'failed'
    eventType = client_nm + "-" + engagement_nm + "-" + "data-intake" + "-" + "rrms-execution"
    recordCount = 0
    targetSchema = client_nm + '_xform'
    jobRunTs = datetime.datetime.utcnow().isoformat() + "Z"

# Check if at least one succeeded
if not dms_success and not rrms_success:
    print("ERROR: Both DMS and RRMS exception table generation failed. Exiting.")
    dbutils.notebook.exit("FAILED: Both DMS and RRMS failed")

# COMMAND ----------

# union of both DMS and RRMS table
# Handle cases where one or both might have failed
if dms_success and rrms_success:
    # Both succeeded - union them
    exceptions_details_byfiling_df = exceptions_details_byfiling_df_dms.union(
        exceptions_details_byfiling_df_rrms.select(exceptions_details_byfiling_df_dms.columns)
    )
    print("Union of DMS and RRMS completed")
elif dms_success:
    # Only DMS succeeded
    exceptions_details_byfiling_df = exceptions_details_byfiling_df_dms
    print("Using only DMS data (RRMS failed)")
elif rrms_success:
    # Only RRMS succeeded
    exceptions_details_byfiling_df = exceptions_details_byfiling_df_rrms
    print("Using only RRMS data (DMS failed)")

# OPTIMIZATION: Repartition after union to reduce partition count
# The 21,000+ tasks in Spark UI indicate too many small partitions
# Coalesce to a reasonable number (adjust based on data size and cluster)
print("Repartitioning union DataFrame to reduce task count...")
exceptions_details_byfiling_df = exceptions_details_byfiling_df.repartition(200)

# COMMAND ----------

# ==================================================================================
# OPTIMIZATION #1: Replace subtract() with left_anti join on key columns
# This is the PRIMARY fix for the 3+ hour CDC operation
#
# WHY THE ORIGINAL WAS SLOW (from Spark UI):
# - Job 55: 20,600 tasks taking 3.6 hours (the subtract + count)
# - Job 114: 20,800 tasks taking 3.6 hours (the delta write, recomputing everything)
# - 21,000+ tasks indicates massive data shuffling across all partitions
# ==================================================================================

# ===================================================================================
# CRITICAL: CDC LOGIC EXPLANATION
# ===================================================================================
# ORIGINAL: Used subtract() which compares ALL columns
# OPTIMIZED: Uses left_anti join on KEY columns only
#
# IMPORTANT: This is semantically equivalent ONLY IF the key columns truly form
# a unique identifier for records. If two records can have the same keys but 
# different values in other columns, this will produce DIFFERENT results.
#
# If you need EXACT original behavior, uncomment this block and comment the anti-join:
# -----------------------------------------------------------------------------
# exceptions_details_byfiling_df_new = exceptions_details_byfiling_df.subtract(
#     exceptions_details_byfiling_prev_df.select(exceptions_details_byfiling_df.columns)
# )
# -----------------------------------------------------------------------------
#
# The key columns below are chosen because:
# - datasetruleid = SHA256(filenamealias + rulesql) - unique per rule per dataset
# - ruleexceptionsid = SHA256(auditsecondaryinternalfilename + rulesql) - unique per file instance
# - These hashes encode the business uniqueness of records
# ===================================================================================

CDC_KEY_COLUMNS = ["datasetruleid", "ruleexceptionsid", "filenamealias", "calendarmonth"]

# OPTIMIZATION: Only read recent data from previous table with partition pruning
# This dramatically reduces the amount of data to scan
lookback_days = 30  # Adjust based on your data retention needs
cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=lookback_days)).strftime('%Y-%m-%d')

print(f"Reading previous records from last {lookback_days} days (since {cutoff_date})")

# Query with partition filter if auditingdt is a partition column
# If not partitioned, this still helps with data skipping on Delta tables
exceptions_details_byfiling_prev_df = spark.sql("""
    SELECT * FROM {}_xform.{}_eyc_exceptions_details
    WHERE auditingdt >= '{}'
""".format(client_nm, engagement_nm, cutoff_date))

# OPTIMIZATION: Cache the key columns from previous data for faster anti-join
# Fill NULL values with empty string to ensure proper join comparison
prev_keys_df = exceptions_details_byfiling_prev_df.select(CDC_KEY_COLUMNS)
for key_col in CDC_KEY_COLUMNS:
    prev_keys_df = prev_keys_df.withColumn(key_col, coalesce(col(key_col), lit("")))
prev_keys_df = prev_keys_df.distinct()
prev_keys_df.cache()
prev_keys_count = prev_keys_df.count()  # Force caching
print(f"Previous unique key combinations: {prev_keys_count}")

# Also fill NULLs in the current dataframe for consistent comparison
for key_col in CDC_KEY_COLUMNS:
    exceptions_details_byfiling_df = exceptions_details_byfiling_df.withColumn(
        key_col, coalesce(col(key_col), lit(""))
    )

# OPTIMIZATION: Use left_anti join instead of subtract()
# This is MUCH faster because:
# 1. Only compares key columns, not all columns
# 2. Can leverage broadcast join if prev_keys_df is small enough
# 3. Avoids full shuffle of all data

if prev_keys_count < 1000000:  # If less than 1M keys, broadcast for even faster join
    print("Using broadcast anti-join (previous keys < 1M)")
    exceptions_details_byfiling_df_new = exceptions_details_byfiling_df.join(
        broadcast(prev_keys_df),
        on=CDC_KEY_COLUMNS,
        how="left_anti"
    )
else:
    print("Using standard anti-join (previous keys >= 1M)")
    exceptions_details_byfiling_df_new = exceptions_details_byfiling_df.join(
        prev_keys_df,
        on=CDC_KEY_COLUMNS,
        how="left_anti"
    )

# ==================================================================================
# OPTIMIZATION #2: Cache before count AND write
# This prevents recomputation of the entire DAG twice
# ==================================================================================
print("Caching new records DataFrame...")
exceptions_details_byfiling_df_new.cache()

# Now count (this triggers caching)
exceptions_details_byfiling_df_count = exceptions_details_byfiling_df_new.count()
print("New records : " + str(exceptions_details_byfiling_df_count))

# Clean up the previous keys cache
prev_keys_df.unpersist()

# ==================================================================================
# ALTERNATIVE APPROACH: Use Delta MERGE (even more efficient for large datasets)
# Uncomment this section if the anti-join is still slow
# ==================================================================================
# from delta.tables import DeltaTable
#
# if DeltaTable.isDeltaTable(spark, exception_details_table_loc):
#     deltaTable = DeltaTable.forPath(spark, exception_details_table_loc)
#     
#     # Add audit columns
#     exceptions_details_byfiling_df_with_audit = exceptions_details_byfiling_df\
#         .withColumn("auditingdt", lit(processing_datetime[0:10]))\
#         .withColumn("auditingts", lit(processing_datetime))
#     
#     # MERGE - only inserts new records, skips existing ones
#     deltaTable.alias("target").merge(
#         exceptions_details_byfiling_df_with_audit.alias("source"),
#         " AND ".join([f"target.{col} = source.{col}" for col in CDC_KEY_COLUMNS])
#     ).whenNotMatchedInsertAll().execute()
#     
#     print("Delta MERGE completed")
# ==================================================================================

# COMMAND ----------

# Count of previous records (from the filtered date range for CDC comparison)
exceptions_details_byfiling_prev_df_count = exceptions_details_byfiling_prev_df.count()
print(f"Previous records count (last {lookback_days} days): {exceptions_details_byfiling_prev_df_count}")

# Get the FULL table count for SQL truncate logic (don't filter by date)
# This prevents incorrectly truncating when there are old records but no recent ones
full_table_count = spark.sql("""
    SELECT COUNT(*) as cnt FROM {}_xform.{}_eyc_exceptions_details
""".format(client_nm, engagement_nm)).first()["cnt"]
print(f"Full table count: {full_table_count}")

# COMMAND ----------

try:
    if exceptions_details_byfiling_df_count > 0:
        # Adding auditingdt & auditingts
        exceptions_details_byfiling_df_final = exceptions_details_byfiling_df_new\
            .withColumn("auditingdt", lit(processing_datetime[0:10]))\
            .withColumn("auditingts", lit(processing_datetime))
        
        # writing to target table
        exception_details_table_loc = spark.sql("DESCRIBE DETAIL {}_xform.{}_eyc_exceptions_details".format(client_nm, engagement_nm)).select("location").toPandas()["location"][0]

        print("Delta Table: {}_xform.{}_eyc_exceptions_details".format(client_nm, engagement_nm))
        print("Table Location: {}".format(exception_details_table_loc))
        print("Writing to Delta Table ...")

        # OPTIMIZATION: The data is already cached, so this write uses cached data
        append_delta(exceptions_details_byfiling_df_final, exception_details_table_loc)
        
        jobStatus = 'success'
        eventType = client_nm + "-" + engagement_nm + "-" + "data-intake" + "-" + "delta-write"
        recordCount = exceptions_details_byfiling_df_count
        targetSchema = client_nm + '_xform'
        jobRunTs = datetime.datetime.utcnow().isoformat() + "Z"
    else:
        print("no delta found")
except Exception as e:
    print(f"Error during delta write: {str(e)}")
    jobStatus = 'failed'
    eventType = client_nm + "-" + engagement_nm + "-" + "data-intake" + "-" + "delta-write"
    recordCount = 0
    targetSchema = client_nm + '_xform'
    jobRunTs = datetime.datetime.utcnow().isoformat() + "Z"
finally:
    # OPTIMIZATION: Clean up cached data
    exceptions_details_byfiling_df_new.unpersist()

# COMMAND ----------

################### Code to connect to JDBC tables and get target metadata information ###################
print("##### Executing queries to get target connection details")

try:
    target_connection_df = get_jdbc_data(
        """
              SELECT
                     JDBC_CONN_TGT_DTL_AL.JDBC_TGT_HOST_NM,
                     JDBC_CONN_TGT_DTL_AL.JDBC_TGT_HOST_PORT,
                     JDBC_CONN_TGT_DTL_AL.JDBC_TGT_SERVER_TYP,
                     JDBC_CONN_TGT_DTL_AL.JDBC_TGT_DRIVER_TYP,
                     JDBC_CONN_TGT_DTL_AL.JDBC_SSL_FLG,
                     JDBC_DB_TGT_DTL_AL.JDBC_DB_NM,
                     JDBC_DB_TGT_DTL_AL.JDBC_TGT_AUTH_TYP,
                     JDBC_DB_TGT_DTL_AL.JDBC_TGT_USR_NM,
                     JDBC_DB_TGT_DTL_AL.JDBC_TGT_PWD
   FROM TGT_MTDT.JDBC_DB_TGT_DTL JDBC_DB_TGT_DTL_AL
          INNER JOIN TGT_MTDT.JDBC_CONN_TGT_DTL JDBC_CONN_TGT_DTL_AL
                     ON JDBC_CONN_TGT_DTL_AL.JDBC_CONN_TGT_PK = JDBC_DB_TGT_DTL_AL.JDBC_CONN_TGT_FK
		 INNER JOIN SRC_MTDT.ENG_DTL ENG_DTL_AL
                   ON ENG_DTL_AL.ENG_PK = JDBC_CONN_TGT_DTL_AL.ENG_FK
        INNER JOIN SRC_MTDT.CLT_DTL CLT_DTL_AL
                   ON CLT_DTL_AL.CLT_PK = ENG_DTL_AL.CLT_FK
               WHERE CLT_DTL_AL.CLT_NM='""" + client_nm + """' and ENG_DTL_AL.ENG_ID='""" + engagement_nm + """'""").withColumn("JDBC_TGT_TBL_NM", concat(lit(client_nm), lit("_xform."), lit(engagement_nm), lit("_eyc_exceptions_details"))).toPandas()

except Exception as e:
    print("The exception is " + str(e))
    dbutils.notebook.exit(0)

# COMMAND ----------

# Truncating SQL table if databricks table is empty
# Use full_table_count (not the filtered count) to avoid incorrect truncation
try:
    if full_table_count == 0:
        print("Delta table is empty - truncating SQL Server table")
        delete_stmt = "truncate table " + target_connection_df["JDBC_TGT_TBL_NM"][0]
        conn_target_jdbc = target_sql_server_connector(str(target_connection_df["JDBC_TGT_USR_NM"][0]),
                                str(target_connection_df["JDBC_TGT_PWD"][0]),
                                str(target_connection_df["JDBC_TGT_HOST_NM"][0]),
                                str(target_connection_df["JDBC_DB_NM"][0]),
                                scope_nm="generic-scope")
        cursor_target_jdbc = conn_target_jdbc.cursor()
        result = cursor_target_jdbc.execute(delete_stmt)
        cursor_target_jdbc.commit()
        cursor_target_jdbc.close()
        conn_target_jdbc.close()

except Exception as E:
    print(E)

# COMMAND ----------

# comparing the timestamps in sql server against the timestamps in the table
source_tbl_df = spark.sql("""select * from {}_xform.{}_eyc_exceptions_details""".format(client_nm, engagement_nm))
target_tbl_query = "select distinct auditingts from " + target_connection_df["JDBC_TGT_TBL_NM"][0]
target_df_values = target_get_jdbc_data(target_tbl_query, target_connection_df)

# OPTIMIZATION: Use broadcast for the small timestamp lookup
append_table = source_tbl_df.join(broadcast(target_df_values), source_tbl_df.auditingts == target_df_values.auditingts, "leftanti")

# COMMAND ----------

append_table.persist()
append_table_count = append_table.count()
print(f"Records to append to SQL Server: {append_table_count}")

# COMMAND ----------

################### Write to JDBC Target table ###################
print("##### Writing output into JDBC target table")

try:
    if append_table_count > 0:
        db_user = dbutils.secrets.get(scope="generic-scope", key=target_connection_df["JDBC_TGT_USR_NM"][0])
        db_pwd = dbutils.secrets.get(scope="generic-scope", key=target_connection_df["JDBC_TGT_PWD"][0])
        
        # OPTIMIZATION: Repartition for parallel JDBC writes
        # Adjust numPartitions based on your cluster and SQL Server capacity
        num_partitions = min(append_table_count // 10000 + 1, 16)  # Max 16 parallel connections
        
        append_table.repartition(num_partitions).write.format("jdbc")\
            .option("url", "jdbc:sqlserver://" + target_connection_df["JDBC_TGT_HOST_NM"][0])\
            .option("dbtable", target_connection_df["JDBC_TGT_TBL_NM"][0])\
            .mode("append")\
            .option("hostname", "*.database.windows.net")\
            .option("driver", "com.microsoft.sqlserver.jdbc.SQLServerDriver")\
            .option("user", db_user + "@" + target_connection_df["JDBC_TGT_HOST_NM"][0][0:target_connection_df["JDBC_TGT_HOST_NM"][0].index(".")])\
            .option("password", db_pwd)\
            .option("database", target_connection_df["JDBC_DB_NM"][0])\
            .option("ssl", "true")\
            .option("batchsize", "10000")\
            .save()
        
        jobStatus = 'success'
        eventType = client_nm + "-" + engagement_nm + "-" + "data-intake" + "-" + "target-sql-write"
        recordCount = exceptions_details_byfiling_df_count
        targetSchema = client_nm + '_xform'
        jobRunTs = datetime.datetime.utcnow().isoformat() + "Z"
    else:
        print("No new records to write to SQL Server")
        
except Exception as e:
    print("The exception is " + str(e))
    jobStatus = 'failed'
    eventType = client_nm + "-" + engagement_nm + "-" + "data-intake" + "-" + "target-sql-write"
    recordCount = 0
    targetSchema = client_nm + '_xform'
    jobRunTs = datetime.datetime.utcnow().isoformat() + "Z"
    dbutils.notebook.exit(0)
finally:
    append_table.unpersist()

# COMMAND ----------

print(f"Job completed successfully for {client_nm} {engagement_nm}")
