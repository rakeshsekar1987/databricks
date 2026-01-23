# Enterprise Microservice Branching & CI/CD Strategy

## For Modular Monorepo with JFrog Artifactory

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Advance Release Branching Strategy](#advance-release-branching-strategy)
3. [Modular Monorepo Structure](#modular-monorepo-structure)
4. [Service-Level Pipeline Isolation](#service-level-pipeline-isolation)
5. [Independent Versioning Per Service](#independent-versioning-per-service)
6. [JFrog Artifact Management](#jfrog-artifact-management)
7. [Environment Promotion Flow](#environment-promotion-flow)
8. [Deployment Strategies](#deployment-strategies)
9. [Feature Flags Integration](#feature-flags-integration)
10. [RBAC and Governance](#rbac-and-governance)
11. [Standardized Templates](#standardized-templates)
12. [Complete Implementation](#complete-implementation)

---

## Architecture Overview

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ENTERPRISE CI/CD ARCHITECTURE                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────────────────────────────────┐
    │                                    GIT REPOSITORY (Monorepo)                              │
    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
    │  │ Service │  │ Service │  │ Service │  │ Service │  │ Service │  │ Shared  │           │
    │  │    A    │  │    B    │  │    C    │  │    D    │  │    E    │  │  Libs   │           │
    │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
    └───────┼────────────┼────────────┼────────────┼────────────┼────────────┼────────────────┘
            │            │            │            │            │            │
            ▼            ▼            ▼            ▼            ▼            ▼
    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                              ISOLATED PIPELINES (Per Service)                              │
    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
    │  │Pipeline │  │Pipeline │  │Pipeline │  │Pipeline │  │Pipeline │  │Pipeline │            │
    │  │   A     │  │   B     │  │   C     │  │   D     │  │   E     │  │  Libs   │            │
    │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │
    └───────┼────────────┼────────────┼────────────┼────────────┼────────────┼────────────────┘
            │            │            │            │            │            │
            ▼            ▼            ▼            ▼            ▼            ▼
    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                              JFROG ARTIFACTORY                                             │
    │  ┌─────────────────────────────────────────────────────────────────────────────────────┐  │
    │  │  Docker Registry    │    Maven/NPM Repo    │    Helm Charts    │    Generic Repo   │  │
    │  │  ─────────────────  │    ──────────────    │    ───────────    │    ────────────   │  │
    │  │  service-a:1.2.0    │    lib-common:3.0    │    chart-a:1.2    │    configs/       │  │
    │  │  service-b:2.1.0    │    lib-auth:2.1      │    chart-b:2.1    │    scripts/       │  │
    │  │  service-c:1.0.5    │    lib-utils:1.5     │    chart-c:1.0    │    templates/     │  │
    │  └─────────────────────────────────────────────────────────────────────────────────────┘  │
    └───────────────────────────────────────────────────────────────────────────────────────────┘
            │            │            │            │            │
            ▼            ▼            ▼            ▼            ▼
    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                              ENVIRONMENT PROMOTION                                         │
    │                                                                                           │
    │     DEV ────────► QA ────────► UAT ────────► PRE-PROD ────────► PRODUCTION               │
    │                                                                                           │
    │  (Auto deploy)  (Auto)     (Manual Gate)   (Manual Gate)      (Canary/Blue-Green)        │
    └───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Advance Release Branching Strategy

### The Challenge: Working on Future Releases

When developers need to work on features for **Release 3.0** while **Release 2.5** is still in progress:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                          ADVANCE RELEASE BRANCHING STRATEGY                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

    Current Release (2.5)              Advance Release (3.0)              Future (3.1+)
    ─────────────────────              ────────────────────               ─────────────
    
                                           advance/3.0
                                               │
                                    ┌──────────┴──────────┐
                                    │                     │
                            feature/ADV-3.0-xxx    feature/ADV-3.0-yyy
                                    │                     │
                                    └──────────┬──────────┘
                                               │
    develop ═══════════════════════════════════╪═══════════════════════════════════════
        │                                      │
        │ Current sprint features              │ (Merge when 2.5 released)
        │                                      │
        ├───────────────┐                      │
        │               │                      │
    feature/2.5-xxx  bugfix/2.5-yyy           │
        │               │                      │
        └───────┬───────┘                      │
                │                              │
                ▼                              │
        release/2.5.0 ─────────────────────────┤
                │                              │
                │ (After 2.5.0 to production)  │
                │                              │
                ▼                              ▼
    master ════════════════════════════════════════════════════════════════════════════
                │
                │
        Tag: v2.5.0
```

### Branch Types for Multi-Release Support

```yaml
# Branch hierarchy for advance releases
branches:
  # Long-lived branches
  master:
    purpose: "Production-ready code"
    protected: true
    
  develop:
    purpose: "Current release integration"
    protected: true
    deploys_to: dev
    
  advance/<version>:
    purpose: "Future release development"
    example: "advance/3.0"
    protected: true
    deploys_to: dev-advance
    created_from: develop
    merges_to: develop (when current release ships)
    
  # Short-lived branches
  feature/<ticket>-<desc>:
    for_current_release: true
    created_from: develop
    merges_to: develop
    
  feature/ADV-<version>-<ticket>-<desc>:
    for_advance_release: true
    example: "feature/ADV-3.0-1234-new-api"
    created_from: advance/<version>
    merges_to: advance/<version>
    
  release/<version>:
    purpose: "Release candidate stabilization"
    created_from: develop
    merges_to: master, develop
```

### Advance Release Workflow

```bash
# ============================================
# SCENARIO: Release 2.5 in progress, working on 3.0 features
# ============================================

# 1. Create advance branch for 3.0 (done once)
git checkout develop
git pull origin develop
git checkout -b advance/3.0
git push -u origin advance/3.0

# 2. Developer starts feature for 3.0
git checkout advance/3.0
git pull origin advance/3.0
git checkout -b feature/ADV-3.0-1234-new-payment-api
# ... develop feature ...
git push -u origin feature/ADV-3.0-1234-new-payment-api
# Create PR to advance/3.0

# 3. Meanwhile, 2.5 features continue on develop
git checkout develop
git checkout -b feature/2.5-5678-fix-login
# ... develop feature ...
# Create PR to develop

# 4. Release 2.5.0
git checkout develop
git checkout -b release/2.5.0
# ... QA, UAT, fixes ...
git checkout master
git merge release/2.5.0
git tag v2.5.0
git push origin master --tags

# 5. After 2.5.0 ships, merge advance/3.0 to develop
git checkout develop
git pull origin develop
git merge advance/3.0
git push origin develop

# 6. Continue 3.0 development on develop
# (advance/3.0 branch can be deleted or kept for tracking)
```

### Managing Multiple Advance Releases

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                       MULTIPLE ADVANCE RELEASES TIMELINE                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

    Time ──────────────────────────────────────────────────────────────────────────────────────►

    Q1 2024                    Q2 2024                    Q3 2024                    Q4 2024
    ────────                   ────────                   ────────                   ────────

    develop (2.5.x)            develop (2.6.x)            develop (3.0.x)            develop (3.1.x)
    ═══════════════════════════════════════════════════════════════════════════════════════════
         │                          │                          │                          │
         │ advance/3.0              │                          │                          │
         │ ─────────►───────────────│───────► (merge to        │                          │
         │                          │          develop)        │                          │
         │                          │                          │                          │
         │ advance/3.1              │ advance/3.1              │                          │
         │ ────────────────────────►│─────────────────────────►│───────► (merge to        │
         │                          │                          │          develop)        │
         │                          │                          │                          │
    release/2.5.0 ──► master   release/2.6.0 ──► master   release/3.0.0 ──► master       │
         │                          │                          │                          │
      v2.5.0                     v2.6.0                     v3.0.0                        │
```

### Advance Release Pipeline Configuration

```yaml
# .github/workflows/advance-release.yaml
name: Advance Release Pipeline

on:
  push:
    branches:
      - 'advance/**'
  pull_request:
    branches:
      - 'advance/**'

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      services: ${{ steps.changes.outputs.services }}
    steps:
      - uses: actions/checkout@v4
      - id: changes
        uses: ./.github/actions/detect-service-changes
        with:
          base_branch: ${{ github.event.pull_request.base.ref || 'advance/3.0' }}

  build-and-test:
    needs: detect-changes
    strategy:
      matrix:
        service: ${{ fromJson(needs.detect-changes.outputs.services) }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build ${{ matrix.service }}
        run: |
          cd services/${{ matrix.service }}
          ./gradlew build
      
      - name: Test ${{ matrix.service }}
        run: |
          cd services/${{ matrix.service }}
          ./gradlew test

  deploy-advance-env:
    needs: build-and-test
    if: github.ref == 'refs/heads/advance/3.0'
    runs-on: ubuntu-latest
    environment: dev-advance
    steps:
      - name: Deploy to Advance Dev Environment
        run: |
          # Deploy to isolated advance environment
          kubectl apply -f k8s/advance-dev/ -n advance-dev
```

---

## Modular Monorepo Structure

### Repository Layout

```
microservices-platform/
├── .github/
│   ├── workflows/
│   │   ├── service-a-pipeline.yaml      # Isolated pipeline for Service A
│   │   ├── service-b-pipeline.yaml      # Isolated pipeline for Service B
│   │   ├── service-c-pipeline.yaml      # Isolated pipeline for Service C
│   │   ├── shared-libs-pipeline.yaml    # Pipeline for shared libraries
│   │   └── templates/                    # Reusable workflow templates
│   │       ├── build-template.yaml
│   │       ├── test-template.yaml
│   │       ├── deploy-template.yaml
│   │       └── security-scan-template.yaml
│   └── CODEOWNERS
│
├── services/
│   ├── user-service/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── helm/
│   │   │   ├── Chart.yaml
│   │   │   ├── values.yaml
│   │   │   ├── values-dev.yaml
│   │   │   ├── values-qa.yaml
│   │   │   ├── values-uat.yaml
│   │   │   ├── values-prod.yaml
│   │   │   └── templates/
│   │   ├── VERSION                       # Independent version file
│   │   ├── CHANGELOG.md
│   │   └── service.yaml                  # Service metadata
│   │
│   ├── order-service/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── helm/
│   │   ├── VERSION
│   │   ├── CHANGELOG.md
│   │   └── service.yaml
│   │
│   ├── payment-service/
│   │   └── ... (same structure)
│   │
│   ├── notification-service/
│   │   └── ... (same structure)
│   │
│   └── api-gateway/
│       └── ... (same structure)
│
├── shared/
│   ├── common-lib/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── VERSION
│   │   └── pom.xml / package.json
│   │
│   ├── auth-lib/
│   │   └── ... (same structure)
│   │
│   └── utils-lib/
│       └── ... (same structure)
│
├── infrastructure/
│   ├── terraform/
│   │   ├── environments/
│   │   │   ├── dev/
│   │   │   ├── qa/
│   │   │   ├── uat/
│   │   │   └── prod/
│   │   └── modules/
│   │
│   ├── kubernetes/
│   │   ├── base/
│   │   └── overlays/
│   │       ├── dev/
│   │       ├── qa/
│   │       ├── uat/
│   │       └── prod/
│   │
│   └── monitoring/
│       ├── prometheus/
│       ├── grafana/
│       └── alerts/
│
├── ci-cd/
│   ├── templates/                        # Reusable CI/CD templates
│   │   ├── Dockerfile.java
│   │   ├── Dockerfile.node
│   │   ├── Jenkinsfile.template
│   │   └── helm-chart-template/
│   │
│   └── scripts/
│       ├── detect-changes.sh
│       ├── version-bump.sh
│       ├── promote-artifact.sh
│       └── rollback.sh
│
├── docs/
│   ├── architecture/
│   ├── runbooks/
│   └── api-specs/
│
└── tools/
    ├── local-dev/
    └── testing/
```

### Service Metadata File

```yaml
# services/user-service/service.yaml
apiVersion: platform.company.io/v1
kind: ServiceMetadata
metadata:
  name: user-service
  team: user-team
  domain: identity
  
spec:
  # Service information
  description: "Manages user authentication and profiles"
  language: java
  framework: spring-boot
  
  # Ownership
  owners:
    - team: user-team
    - lead: john.doe@company.com
  oncall:
    pagerduty: user-service-pd
    slack: "#user-service-alerts"
  
  # Dependencies
  dependencies:
    internal:
      - service: auth-lib
        version: ">=2.0.0"
      - service: common-lib
        version: ">=3.0.0"
    external:
      - name: postgresql
        version: "15.x"
      - name: redis
        version: "7.x"
  
  # Build configuration
  build:
    type: gradle
    dockerfile: Dockerfile
    context: .
    
  # Deployment configuration
  deployment:
    strategy: canary
    canary:
      steps: [10, 25, 50, 100]
      interval: 5m
    resources:
      requests:
        cpu: 200m
        memory: 512Mi
      limits:
        cpu: 1000m
        memory: 1Gi
    replicas:
      dev: 1
      qa: 2
      uat: 2
      prod: 5
      
  # Quality gates
  quality:
    coverage_threshold: 80
    sonar_gate: true
    security_scan: true
    
  # Feature flags
  feature_flags:
    provider: launchdarkly
    project: user-service
```

---

## Service-Level Pipeline Isolation

### Principle #1: Isolated Pipelines per Service

```yaml
# .github/workflows/user-service-pipeline.yaml
name: User Service Pipeline

on:
  push:
    branches: [develop, 'release/**', master, 'advance/**']
    paths:
      - 'services/user-service/**'
      - 'shared/common-lib/**'      # Trigger on shared lib changes
      - 'shared/auth-lib/**'
  pull_request:
    branches: [develop, 'release/**', 'advance/**']
    paths:
      - 'services/user-service/**'
      - 'shared/common-lib/**'
      - 'shared/auth-lib/**'

env:
  SERVICE_NAME: user-service
  SERVICE_PATH: services/user-service
  JFROG_REGISTRY: company.jfrog.io
  JFROG_REPO: docker-local

jobs:
  # ============================================
  # DETECT VERSION AND CHANGES
  # ============================================
  setup:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
      should_deploy: ${{ steps.check.outputs.should_deploy }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Get Service Version
        id: version
        run: |
          VERSION=$(cat ${{ env.SERVICE_PATH }}/VERSION)
          COMMIT_SHA=$(git rev-parse --short HEAD)
          
          if [[ "${{ github.ref }}" == refs/heads/release/* ]]; then
            echo "version=${VERSION}-rc.${GITHUB_RUN_NUMBER}" >> $GITHUB_OUTPUT
          elif [[ "${{ github.ref }}" == "refs/heads/master" ]]; then
            echo "version=${VERSION}" >> $GITHUB_OUTPUT
          else
            echo "version=${VERSION}-${COMMIT_SHA}" >> $GITHUB_OUTPUT
          fi
      
      - name: Check if should deploy
        id: check
        run: |
          if [[ "${{ github.event_name }}" == "push" ]]; then
            echo "should_deploy=true" >> $GITHUB_OUTPUT
          else
            echo "should_deploy=false" >> $GITHUB_OUTPUT
          fi

  # ============================================
  # BUILD AND TEST
  # ============================================
  build:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
          cache: 'gradle'
      
      - name: Build
        run: ./gradlew build -x test
        working-directory: ${{ env.SERVICE_PATH }}
      
      - name: Upload Build Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ env.SERVICE_NAME }}-build
          path: ${{ env.SERVICE_PATH }}/build/libs/

  test:
    needs: setup
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
          cache: 'gradle'
      
      - name: Unit Tests
        run: ./gradlew test
        working-directory: ${{ env.SERVICE_PATH }}
      
      - name: Integration Tests
        run: ./gradlew integrationTest
        working-directory: ${{ env.SERVICE_PATH }}
      
      - name: Code Coverage
        run: ./gradlew jacocoTestReport
        working-directory: ${{ env.SERVICE_PATH }}
      
      - name: Check Coverage Threshold
        run: |
          COVERAGE=$(cat build/reports/jacoco/test/jacocoTestReport.xml | grep -o 'INSTRUCTION.*' | head -1 | grep -o 'covered="[0-9]*"' | grep -o '[0-9]*')
          if [ "$COVERAGE" -lt 80 ]; then
            echo "Coverage $COVERAGE% is below threshold 80%"
            exit 1
          fi
        working-directory: ${{ env.SERVICE_PATH }}

  # ============================================
  # SECURITY SCAN
  # ============================================
  security:
    needs: [build, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: SAST Scan
        uses: github/codeql-action/analyze@v2
        with:
          languages: java
      
      - name: Dependency Check
        run: ./gradlew dependencyCheckAnalyze
        working-directory: ${{ env.SERVICE_PATH }}
      
      - name: Container Scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: ${{ env.SERVICE_PATH }}
          severity: 'CRITICAL,HIGH'

  # ============================================
  # BUILD AND PUSH DOCKER IMAGE TO JFROG
  # ============================================
  docker:
    needs: [setup, build, test, security]
    if: needs.setup.outputs.should_deploy == 'true'
    runs-on: ubuntu-latest
    outputs:
      image_tag: ${{ steps.push.outputs.image_tag }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Download Build Artifacts
        uses: actions/download-artifact@v4
        with:
          name: ${{ env.SERVICE_NAME }}-build
          path: ${{ env.SERVICE_PATH }}/build/libs/
      
      - name: Login to JFrog
        uses: docker/login-action@v3
        with:
          registry: ${{ env.JFROG_REGISTRY }}
          username: ${{ secrets.JFROG_USERNAME }}
          password: ${{ secrets.JFROG_PASSWORD }}
      
      - name: Build and Push Docker Image
        id: push
        run: |
          IMAGE_TAG="${{ env.JFROG_REGISTRY }}/${{ env.JFROG_REPO }}/${{ env.SERVICE_NAME }}:${{ needs.setup.outputs.version }}"
          
          docker build -t $IMAGE_TAG .
          docker push $IMAGE_TAG
          
          echo "image_tag=$IMAGE_TAG" >> $GITHUB_OUTPUT
        working-directory: ${{ env.SERVICE_PATH }}
      
      - name: Update JFrog Build Info
        run: |
          jfrog rt build-add-git ${{ env.SERVICE_NAME }} ${{ github.run_number }}
          jfrog rt build-publish ${{ env.SERVICE_NAME }} ${{ github.run_number }}

  # ============================================
  # PUSH HELM CHART TO JFROG
  # ============================================
  helm:
    needs: [setup, docker]
    if: needs.setup.outputs.should_deploy == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Package Helm Chart
        run: |
          # Update chart version
          sed -i "s/version:.*/version: ${{ needs.setup.outputs.version }}/" helm/Chart.yaml
          sed -i "s/appVersion:.*/appVersion: ${{ needs.setup.outputs.version }}/" helm/Chart.yaml
          
          # Package chart
          helm package helm/ -d /tmp/charts/
        working-directory: ${{ env.SERVICE_PATH }}
      
      - name: Push Helm Chart to JFrog
        run: |
          curl -u ${{ secrets.JFROG_USERNAME }}:${{ secrets.JFROG_PASSWORD }} \
            -T /tmp/charts/${{ env.SERVICE_NAME }}-${{ needs.setup.outputs.version }}.tgz \
            "${{ env.JFROG_REGISTRY }}/helm-local/${{ env.SERVICE_NAME }}/"

  # ============================================
  # DEPLOY TO ENVIRONMENTS
  # ============================================
  deploy-dev:
    needs: [setup, docker, helm]
    if: github.ref == 'refs/heads/develop' || startsWith(github.ref, 'refs/heads/advance/')
    runs-on: ubuntu-latest
    environment: development
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Dev
        run: |
          helm upgrade --install ${{ env.SERVICE_NAME }} \
            oci://${{ env.JFROG_REGISTRY }}/helm-local/${{ env.SERVICE_NAME }} \
            --version ${{ needs.setup.outputs.version }} \
            -f ${{ env.SERVICE_PATH }}/helm/values-dev.yaml \
            -n dev \
            --set image.tag=${{ needs.setup.outputs.version }}

  deploy-qa:
    needs: [setup, docker, helm]
    if: startsWith(github.ref, 'refs/heads/release/')
    runs-on: ubuntu-latest
    environment: qa
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to QA
        run: |
          helm upgrade --install ${{ env.SERVICE_NAME }} \
            oci://${{ env.JFROG_REGISTRY }}/helm-local/${{ env.SERVICE_NAME }} \
            --version ${{ needs.setup.outputs.version }} \
            -f ${{ env.SERVICE_PATH }}/helm/values-qa.yaml \
            -n qa \
            --set image.tag=${{ needs.setup.outputs.version }}

  deploy-uat:
    needs: [deploy-qa]
    if: startsWith(github.ref, 'refs/heads/release/')
    runs-on: ubuntu-latest
    environment: uat
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to UAT
        run: |
          helm upgrade --install ${{ env.SERVICE_NAME }} \
            oci://${{ env.JFROG_REGISTRY }}/helm-local/${{ env.SERVICE_NAME }} \
            --version ${{ needs.setup.outputs.version }} \
            -f ${{ env.SERVICE_PATH }}/helm/values-uat.yaml \
            -n uat \
            --set image.tag=${{ needs.setup.outputs.version }}

  deploy-production:
    needs: [setup, docker, helm]
    if: github.ref == 'refs/heads/master'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Canary Deploy to Production
        run: |
          # Deploy canary (10%)
          helm upgrade --install ${{ env.SERVICE_NAME }}-canary \
            oci://${{ env.JFROG_REGISTRY }}/helm-local/${{ env.SERVICE_NAME }} \
            --version ${{ needs.setup.outputs.version }} \
            -f ${{ env.SERVICE_PATH }}/helm/values-prod.yaml \
            -n production \
            --set image.tag=${{ needs.setup.outputs.version }} \
            --set canary.enabled=true \
            --set canary.weight=10
      
      - name: Monitor Canary (5 min)
        run: |
          sleep 300
          ./ci-cd/scripts/check-canary-health.sh ${{ env.SERVICE_NAME }} production
      
      - name: Promote to Full Production
        run: |
          helm upgrade --install ${{ env.SERVICE_NAME }} \
            oci://${{ env.JFROG_REGISTRY }}/helm-local/${{ env.SERVICE_NAME }} \
            --version ${{ needs.setup.outputs.version }} \
            -f ${{ env.SERVICE_PATH }}/helm/values-prod.yaml \
            -n production \
            --set image.tag=${{ needs.setup.outputs.version }}
          
          # Remove canary
          helm uninstall ${{ env.SERVICE_NAME }}-canary -n production || true
```

### Benefits of Isolated Pipelines

```yaml
# Benefits summary
isolated_pipelines:
  faster_builds:
    description: "Only build/test changed services"
    impact: "80% reduction in CI time"
    
  reduced_blast_radius:
    description: "Failure in Service A doesn't block Service B"
    impact: "Independent release cycles"
    
  deployment_autonomy:
    description: "Teams deploy their services independently"
    impact: "Faster time to production"
    
  simpler_rollback:
    description: "Rollback single service without affecting others"
    impact: "Reduced risk, faster recovery"
```

---

## Independent Versioning Per Service

### Principle #2: Semantic Versioning Per Service

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                          INDEPENDENT VERSIONING STRATEGY                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

    Each service has its own VERSION file and follows SemVer independently:

    services/
    ├── user-service/
    │   └── VERSION         →  2.3.1
    │
    ├── order-service/
    │   └── VERSION         →  1.8.0
    │
    ├── payment-service/
    │   └── VERSION         →  3.0.0
    │
    └── notification-service/
        └── VERSION         →  1.2.5

    Timeline Example:
    ─────────────────
    
    Jan 15: user-service 2.3.0 → 2.3.1 (patch)
    Jan 16: order-service 1.7.0 → 1.8.0 (minor)
    Jan 18: payment-service 2.9.0 → 3.0.0 (breaking change)
    Jan 20: user-service 2.3.1 → 2.4.0 (new feature)
    
    Services release independently based on their own roadmaps!
```

### VERSION File and Changelog

```bash
# services/user-service/VERSION
2.3.1
```

```markdown
# services/user-service/CHANGELOG.md

# Changelog

All notable changes to user-service will be documented in this file.

## [2.3.1] - 2024-01-15
### Fixed
- Fixed null pointer in token refresh logic
- Resolved race condition in session management

## [2.3.0] - 2024-01-10
### Added
- OAuth2 support for external providers
- MFA enrollment API
### Changed
- Improved password hashing algorithm

## [2.2.0] - 2024-01-05
### Added
- User profile image upload
### Deprecated
- Legacy authentication endpoint (will be removed in 3.0.0)
```

### Automated Version Management

```yaml
# .github/workflows/version-management.yaml
name: Version Management

on:
  pull_request:
    types: [closed]
    branches: [develop]

jobs:
  bump-version:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Detect Changed Services
        id: changes
        run: |
          CHANGED_SERVICES=$(git diff --name-only ${{ github.event.pull_request.base.sha }} ${{ github.sha }} | \
            grep '^services/' | cut -d'/' -f2 | sort -u | tr '\n' ' ')
          echo "services=$CHANGED_SERVICES" >> $GITHUB_OUTPUT
      
      - name: Determine Version Bump Type
        id: bump-type
        run: |
          PR_TITLE="${{ github.event.pull_request.title }}"
          PR_LABELS="${{ join(github.event.pull_request.labels.*.name, ' ') }}"
          
          if [[ "$PR_LABELS" == *"breaking-change"* ]] || [[ "$PR_TITLE" == *"BREAKING"* ]]; then
            echo "bump=major" >> $GITHUB_OUTPUT
          elif [[ "$PR_TITLE" == feat* ]] || [[ "$PR_LABELS" == *"feature"* ]]; then
            echo "bump=minor" >> $GITHUB_OUTPUT
          else
            echo "bump=patch" >> $GITHUB_OUTPUT
          fi
      
      - name: Bump Versions
        run: |
          for SERVICE in ${{ steps.changes.outputs.services }}; do
            VERSION_FILE="services/$SERVICE/VERSION"
            if [ -f "$VERSION_FILE" ]; then
              CURRENT=$(cat $VERSION_FILE)
              IFS='.' read -ra PARTS <<< "$CURRENT"
              MAJOR=${PARTS[0]}
              MINOR=${PARTS[1]}
              PATCH=${PARTS[2]}
              
              case "${{ steps.bump-type.outputs.bump }}" in
                major)
                  NEW_VERSION="$((MAJOR+1)).0.0"
                  ;;
                minor)
                  NEW_VERSION="$MAJOR.$((MINOR+1)).0"
                  ;;
                patch)
                  NEW_VERSION="$MAJOR.$MINOR.$((PATCH+1))"
                  ;;
              esac
              
              echo "$NEW_VERSION" > "$VERSION_FILE"
              echo "Bumped $SERVICE from $CURRENT to $NEW_VERSION"
            fi
          done
      
      - name: Commit Version Changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add services/*/VERSION
          git commit -m "chore: bump service versions [skip ci]" || exit 0
          git push
```

### Version Tagging Strategy

```bash
# Tag format: <service-name>/v<version>
# Examples:
git tag user-service/v2.3.1
git tag order-service/v1.8.0
git tag payment-service/v3.0.0

# View all versions of a service
git tag -l "user-service/*"

# Git release notes per service
git log user-service/v2.3.0..user-service/v2.3.1 --oneline
```

---

## JFrog Artifact Management

### JFrog Repository Structure

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              JFROG ARTIFACTORY STRUCTURE                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

    company.jfrog.io/
    │
    ├── docker-dev-local/           # Development builds
    │   ├── user-service/
    │   │   ├── 2.3.1-abc123        # Commit-based tags
    │   │   ├── 2.3.1-def456
    │   │   └── latest-develop
    │   ├── order-service/
    │   └── payment-service/
    │
    ├── docker-rc-local/            # Release candidates
    │   ├── user-service/
    │   │   ├── 2.3.1-rc.1
    │   │   ├── 2.3.1-rc.2
    │   │   └── 2.3.1-rc.3
    │   └── ...
    │
    ├── docker-release-local/       # Production releases
    │   ├── user-service/
    │   │   ├── 2.3.0
    │   │   ├── 2.3.1
    │   │   └── latest
    │   └── ...
    │
    ├── helm-local/                 # Helm charts
    │   ├── user-service/
    │   │   ├── user-service-2.3.1.tgz
    │   │   └── index.yaml
    │   └── ...
    │
    ├── libs-release-local/         # Shared libraries (Maven/NPM)
    │   ├── com/company/common-lib/
    │   │   ├── 3.0.0/
    │   │   └── 3.0.1/
    │   ├── com/company/auth-lib/
    │   └── ...
    │
    └── generic-local/              # Generic artifacts
        ├── configs/
        ├── scripts/
        └── templates/
```

### JFrog Integration Scripts

```bash
#!/bin/bash
# ci-cd/scripts/jfrog-promote.sh
# Promotes artifacts between JFrog repositories

set -e

SERVICE_NAME=$1
VERSION=$2
SOURCE_REPO=$3
TARGET_REPO=$4

echo "Promoting $SERVICE_NAME:$VERSION from $SOURCE_REPO to $TARGET_REPO"

# Promote Docker image
jfrog rt copy \
  "$SOURCE_REPO/$SERVICE_NAME/$VERSION" \
  "$TARGET_REPO/$SERVICE_NAME/$VERSION" \
  --flat

# Promote Helm chart
jfrog rt copy \
  "helm-local/$SERVICE_NAME/$SERVICE_NAME-$VERSION.tgz" \
  "helm-release-local/$SERVICE_NAME/$SERVICE_NAME-$VERSION.tgz" \
  --flat

# Update build info
jfrog rt build-promote \
  "$SERVICE_NAME" \
  "$GITHUB_RUN_NUMBER" \
  "$TARGET_REPO" \
  --status "Promoted" \
  --comment "Promoted to $TARGET_REPO"

echo "Promotion complete!"
```

```yaml
# JFrog Xray security scanning
xray_policies:
  security_policy:
    name: "Production Security Policy"
    rules:
      - name: "Block Critical Vulnerabilities"
        criteria:
          min_severity: critical
        actions:
          block_download: true
          notify:
            - security-team@company.com
      
      - name: "Warn on High Vulnerabilities"
        criteria:
          min_severity: high
        actions:
          block_download: false
          notify:
            - dev-team@company.com
            
  license_policy:
    name: "License Compliance"
    rules:
      - name: "Block GPL"
        criteria:
          banned_licenses:
            - GPL-3.0
            - AGPL-3.0
        actions:
          block_download: true
```

### Artifact Lifecycle Management

```yaml
# JFrog artifact retention policy
retention_policies:
  docker-dev-local:
    description: "Development builds"
    rules:
      - keep_last: 10  # Per service
      - max_age_days: 14
      - exclude_patterns:
          - "*-develop"  # Keep latest develop
          
  docker-rc-local:
    description: "Release candidates"
    rules:
      - keep_last: 5  # Per version
      - max_age_days: 30
      
  docker-release-local:
    description: "Production releases"
    rules:
      - keep_all: true  # Never auto-delete
      - immutable: true  # Cannot be overwritten
```

---

## Environment Promotion Flow

### Artifact-Based Promotion

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ARTIFACT PROMOTION FLOW                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

    Build Once, Deploy Many Times:

                                    ┌─────────────────────────────────────────────────┐
                                    │              JFROG ARTIFACTORY                   │
                                    └─────────────────────────────────────────────────┘
                                                         │
    ┌────────────────────────────────────────────────────┼────────────────────────────────────────┐
    │                                                    │                                        │
    │  1. BUILD                                          │                                        │
    │  ───────                                           │                                        │
    │                                                    ▼                                        │
    │  develop ──────► Build ──────► docker-dev-local/user-service:2.3.1-abc123                  │
    │                    │                                                                        │
    │                    └──────────► helm-local/user-service-2.3.1-abc123.tgz                   │
    │                                                                                             │
    ├─────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                             │
    │  2. DEV DEPLOYMENT                                                                          │
    │  ─────────────────                                                                          │
    │                                                                                             │
    │  docker-dev-local/user-service:2.3.1-abc123 ──────► DEV Environment                        │
    │                    │                                      │                                 │
    │                    │                                      ▼                                 │
    │                    │                               Smoke Tests ✓                            │
    │                                                                                             │
    ├─────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                             │
    │  3. RELEASE CUT (Promote to RC)                                                             │
    │  ──────────────────────────────                                                             │
    │                                                                                             │
    │  release/2.5.0 ──────► Promote ──────► docker-rc-local/user-service:2.3.1-rc.1             │
    │                                                    │                                        │
    │                                                    ▼                                        │
    │                                             QA Environment                                  │
    │                                                    │                                        │
    │                                                    ▼                                        │
    │                                            QA Tests + Bug Fix                               │
    │                                                    │                                        │
    │                                                    ▼                                        │
    │                              docker-rc-local/user-service:2.3.1-rc.2 (if fixes needed)     │
    │                                                                                             │
    ├─────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                             │
    │  4. UAT PROMOTION                                                                           │
    │  ────────────────                                                                           │
    │                                                                                             │
    │  QA Approved ──────► Same docker-rc-local/user-service:2.3.1-rc.2 ──────► UAT Environment  │
    │                                                    │                                        │
    │                                                    ▼                                        │
    │                                             UAT Sign-off ✓                                  │
    │                                                                                             │
    ├─────────────────────────────────────────────────────────────────────────────────────────────┤
    │                                                                                             │
    │  5. PRODUCTION RELEASE                                                                      │
    │  ─────────────────────                                                                      │
    │                                                                                             │
    │  master merge ──────► Promote ──────► docker-release-local/user-service:2.3.1              │
    │                         │                          │                                        │
    │                         │                          ▼                                        │
    │                         │                   PRODUCTION (Canary)                             │
    │                         │                          │                                        │
    │                         └──── Tag: user-service/v2.3.1                                     │
    │                                                                                             │
    └─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Promotion Pipeline

```yaml
# .github/workflows/promote-artifact.yaml
name: Promote Artifact

on:
  workflow_dispatch:
    inputs:
      service:
        description: 'Service to promote'
        required: true
        type: choice
        options:
          - user-service
          - order-service
          - payment-service
      version:
        description: 'Version to promote (e.g., 2.3.1-rc.2)'
        required: true
      target_environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - qa
          - uat
          - production

jobs:
  promote:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.target_environment }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup JFrog CLI
        uses: jfrog/setup-jfrog-cli@v3
        with:
          version: latest
        env:
          JF_URL: ${{ secrets.JFROG_URL }}
          JF_ACCESS_TOKEN: ${{ secrets.JFROG_TOKEN }}
      
      - name: Determine Source and Target Repos
        id: repos
        run: |
          case "${{ github.event.inputs.target_environment }}" in
            qa)
              echo "source=docker-dev-local" >> $GITHUB_OUTPUT
              echo "target=docker-rc-local" >> $GITHUB_OUTPUT
              ;;
            uat)
              echo "source=docker-rc-local" >> $GITHUB_OUTPUT
              echo "target=docker-rc-local" >> $GITHUB_OUTPUT  # Same repo, different tag
              ;;
            production)
              echo "source=docker-rc-local" >> $GITHUB_OUTPUT
              echo "target=docker-release-local" >> $GITHUB_OUTPUT
              ;;
          esac
      
      - name: Security Scan Before Promotion
        run: |
          jfrog xray scan \
            --repo ${{ steps.repos.outputs.source }} \
            --path "${{ github.event.inputs.service }}/${{ github.event.inputs.version }}" \
            --fail-on-security-issues
      
      - name: Promote Artifact
        run: |
          ./ci-cd/scripts/jfrog-promote.sh \
            "${{ github.event.inputs.service }}" \
            "${{ github.event.inputs.version }}" \
            "${{ steps.repos.outputs.source }}" \
            "${{ steps.repos.outputs.target }}"
      
      - name: Deploy to Environment
        run: |
          ENV=${{ github.event.inputs.target_environment }}
          SERVICE=${{ github.event.inputs.service }}
          VERSION=${{ github.event.inputs.version }}
          
          helm upgrade --install $SERVICE \
            oci://$JFROG_REGISTRY/helm-local/$SERVICE \
            --version $VERSION \
            -f services/$SERVICE/helm/values-$ENV.yaml \
            -n $ENV \
            --set image.tag=$VERSION
      
      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "✅ ${{ github.event.inputs.service }}:${{ github.event.inputs.version }} promoted to ${{ github.event.inputs.target_environment }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Deployment Strategies

### Principle #3: Progressive Delivery

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              DEPLOYMENT STRATEGIES                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
    │                                    CANARY DEPLOYMENT                                         │
    │                                                                                             │
    │    Time 0:    [v1.0] [v1.0] [v1.0] [v1.0] [v1.0]  ─── 100% stable                          │
    │                                                                                             │
    │    Time 1:    [v1.0] [v1.0] [v1.0] [v1.0] [v1.1]  ─── 10% canary                           │
    │                      │                     │                                                │
    │                      │    Monitor 5 min    │                                                │
    │                      ▼                     ▼                                                │
    │    Time 2:    [v1.0] [v1.0] [v1.0] [v1.1] [v1.1]  ─── 25% canary                           │
    │                      │                     │                                                │
    │                      │    Monitor 5 min    │                                                │
    │                      ▼                     ▼                                                │
    │    Time 3:    [v1.0] [v1.0] [v1.1] [v1.1] [v1.1]  ─── 50% canary                           │
    │                      │                     │                                                │
    │                      │    Monitor 5 min    │                                                │
    │                      ▼                     ▼                                                │
    │    Time 4:    [v1.1] [v1.1] [v1.1] [v1.1] [v1.1]  ─── 100% new version                     │
    │                                                                                             │
    └─────────────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
    │                                   BLUE/GREEN DEPLOYMENT                                      │
    │                                                                                             │
    │                            LOAD BALANCER                                                    │
    │                                  │                                                          │
    │              ┌───────────────────┴───────────────────┐                                      │
    │              │                                       │                                      │
    │              ▼                                       ▼                                      │
    │    ┌─────────────────┐                     ┌─────────────────┐                              │
    │    │      BLUE       │                     │      GREEN      │                              │
    │    │     (v1.0)      │                     │     (v1.1)      │                              │
    │    │    [ACTIVE]     │ ◄── Switch ───►    │   [STANDBY]     │                              │
    │    │                 │                     │                 │                              │
    │    │  5 replicas     │                     │  5 replicas     │                              │
    │    └─────────────────┘                     └─────────────────┘                              │
    │                                                                                             │
    │    Switch is instant! Rollback = switch back to Blue                                       │
    └─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Kubernetes Canary Implementation

```yaml
# services/user-service/helm/templates/canary.yaml
{{- if .Values.canary.enabled }}
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: {{ .Release.Name }}
spec:
  replicas: {{ .Values.replicas }}
  strategy:
    canary:
      canaryService: {{ .Release.Name }}-canary
      stableService: {{ .Release.Name }}-stable
      trafficRouting:
        istio:
          virtualService:
            name: {{ .Release.Name }}-vsvc
            routes:
              - primary
      steps:
        - setWeight: 10
        - pause: { duration: 5m }
        - setWeight: 25
        - pause: { duration: 5m }
        - setWeight: 50
        - pause: { duration: 5m }
        - setWeight: 75
        - pause: { duration: 5m }
        - setWeight: 100
      analysis:
        templates:
          - templateName: {{ .Release.Name }}-analysis
        startingStep: 1
        args:
          - name: service-name
            value: {{ .Release.Name }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
        - name: {{ .Release.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports:
            - containerPort: 8080
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: {{ .Release.Name }}-analysis
spec:
  args:
    - name: service-name
  metrics:
    - name: success-rate
      interval: 1m
      successCondition: result[0] >= 0.99
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            sum(rate(http_requests_total{service="{{args.service-name}}",status=~"2.."}[5m])) /
            sum(rate(http_requests_total{service="{{args.service-name}}"}[5m]))
    - name: latency-p99
      interval: 1m
      successCondition: result[0] <= 100
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service="{{args.service-name}}"}[5m])) by (le))
{{- end }}
```

### Rollback Script

```bash
#!/bin/bash
# ci-cd/scripts/rollback.sh
# Rollback a service to previous version

set -e

SERVICE_NAME=$1
ENVIRONMENT=$2
TARGET_VERSION=$3  # Optional, defaults to previous

if [ -z "$TARGET_VERSION" ]; then
  # Get previous version from Helm history
  TARGET_VERSION=$(helm history $SERVICE_NAME -n $ENVIRONMENT --max 2 -o json | jq -r '.[1].chart' | sed 's/.*-//')
  echo "Rolling back to previous version: $TARGET_VERSION"
fi

# Check if version exists in JFrog
ARTIFACT_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" \
  -u $JFROG_USER:$JFROG_PASSWORD \
  "$JFROG_URL/docker-release-local/$SERVICE_NAME/$TARGET_VERSION/manifest.json")

if [ "$ARTIFACT_EXISTS" != "200" ]; then
  echo "Error: Version $TARGET_VERSION not found in JFrog"
  exit 1
fi

# Execute rollback
echo "Rolling back $SERVICE_NAME to $TARGET_VERSION in $ENVIRONMENT"

helm rollback $SERVICE_NAME -n $ENVIRONMENT

# Or deploy specific version
# helm upgrade --install $SERVICE_NAME \
#   oci://$JFROG_REGISTRY/helm-local/$SERVICE_NAME \
#   --version $TARGET_VERSION \
#   -f services/$SERVICE_NAME/helm/values-$ENVIRONMENT.yaml \
#   -n $ENVIRONMENT

# Verify rollback
kubectl rollout status deployment/$SERVICE_NAME -n $ENVIRONMENT

echo "Rollback complete!"

# Notify
curl -X POST $SLACK_WEBHOOK \
  -H 'Content-type: application/json' \
  -d "{\"text\": \"🔄 Rollback: $SERVICE_NAME rolled back to $TARGET_VERSION in $ENVIRONMENT\"}"
```

---

## Feature Flags Integration

### Feature Flag Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              FEATURE FLAG INTEGRATION                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                               FEATURE FLAG PROVIDER                                        │
    │                        (LaunchDarkly / Flagsmith / Split.io)                              │
    │                                                                                           │
    │   ┌───────────────────────────────────────────────────────────────────────────────────┐  │
    │   │  Feature: new-checkout-flow                                                        │  │
    │   │  ─────────────────────────────                                                     │  │
    │   │  DEV:        100% enabled                                                          │  │
    │   │  QA:         100% enabled                                                          │  │
    │   │  UAT:        100% enabled                                                          │  │
    │   │  PRODUCTION: 10% enabled (gradual rollout)                                         │  │
    │   └───────────────────────────────────────────────────────────────────────────────────┘  │
    └───────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              │ SDK
                                              ▼
    ┌───────────────────────────────────────────────────────────────────────────────────────────┐
    │                                   MICROSERVICES                                            │
    │                                                                                           │
    │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
    │   │  User Service   │  │ Order Service   │  │Payment Service  │  │  UI Service     │      │
    │   │                 │  │                 │  │                 │  │                 │      │
    │   │ if (isEnabled(  │  │ if (isEnabled(  │  │ if (isEnabled(  │  │ if (isEnabled(  │      │
    │   │   "new-flow"))  │  │   "new-flow"))  │  │   "new-flow"))  │  │   "new-flow"))  │      │
    │   │   newFlow()     │  │   newFlow()     │  │   newFlow()     │  │   newFlow()     │      │
    │   │ else            │  │ else            │  │ else            │  │ else            │      │
    │   │   oldFlow()     │  │   oldFlow()     │  │   oldFlow()     │  │   oldFlow()     │      │
    │   └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘      │
    └───────────────────────────────────────────────────────────────────────────────────────────┘
```

### Feature Flag Implementation

```java
// Java Spring Boot implementation
@Service
public class CheckoutService {
    
    private final FeatureFlagClient featureFlags;
    private final NewCheckoutFlow newCheckoutFlow;
    private final LegacyCheckoutFlow legacyCheckoutFlow;
    
    public CheckoutResult processCheckout(CheckoutRequest request, User user) {
        // Feature flag evaluation with user context
        boolean useNewFlow = featureFlags.isEnabled(
            "new-checkout-flow",
            FeatureContext.builder()
                .user(user.getId())
                .attributes(Map.of(
                    "plan", user.getPlan(),
                    "region", user.getRegion(),
                    "beta_tester", user.isBetaTester()
                ))
                .build()
        );
        
        if (useNewFlow) {
            return newCheckoutFlow.process(request);
        } else {
            return legacyCheckoutFlow.process(request);
        }
    }
}
```

```typescript
// TypeScript/React implementation
import { useFeatureFlag } from '@launchdarkly/react-client-sdk';

const CheckoutPage: React.FC = () => {
  const showNewCheckout = useFeatureFlag('new-checkout-flow', false);
  
  return (
    <div>
      {showNewCheckout ? (
        <NewCheckoutComponent />
      ) : (
        <LegacyCheckoutComponent />
      )}
    </div>
  );
};
```

### Feature Flag Lifecycle

```yaml
# Feature flag lifecycle management
feature_flag_lifecycle:
  stages:
    1_development:
      description: "Flag created, enabled in dev"
      environments:
        dev: 100%
        qa: 0%
        uat: 0%
        prod: 0%
    
    2_testing:
      description: "Enabled in QA for testing"
      environments:
        dev: 100%
        qa: 100%
        uat: 0%
        prod: 0%
    
    3_uat:
      description: "Enabled in UAT for acceptance"
      environments:
        dev: 100%
        qa: 100%
        uat: 100%
        prod: 0%
    
    4_gradual_rollout:
      description: "Gradual production rollout"
      environments:
        dev: 100%
        qa: 100%
        uat: 100%
        prod: 10%  # Start with 10%
      rollout_schedule:
        - day_1: 10%
        - day_3: 25%
        - day_5: 50%
        - day_7: 75%
        - day_10: 100%
    
    5_full_rollout:
      description: "Fully enabled in production"
      environments:
        all: 100%
    
    6_cleanup:
      description: "Remove flag and dead code"
      actions:
        - remove_flag_checks
        - delete_old_code_path
        - delete_flag_from_provider
        - update_documentation
```

---

## RBAC and Governance

### Principle #4: Role-Based Access Control

```yaml
# RBAC Configuration
rbac:
  roles:
    developer:
      description: "Regular developer"
      permissions:
        - read: all
        - write: feature/*, bugfix/*
        - merge: to develop (with approval)
        - deploy: dev
      restrictions:
        - cannot_merge: master, release/*
        - cannot_deploy: qa, uat, prod
    
    senior_developer:
      description: "Senior/Lead developer"
      permissions:
        - read: all
        - write: all except master
        - merge: to develop
        - approve: feature/*, bugfix/*
        - deploy: dev, qa
      restrictions:
        - cannot_merge: master
        - cannot_deploy: uat, prod
    
    qa_engineer:
      description: "QA team member"
      permissions:
        - read: all
        - write: bugfix/* (on release branches)
        - deploy: qa
        - approve: qa deployments
      restrictions:
        - cannot_deploy: uat, prod
    
    release_manager:
      description: "Release management team"
      permissions:
        - read: all
        - write: release/*, hotfix/*
        - merge: to master
        - approve: release deployments
        - deploy: qa, uat, preprod
        - promote: artifacts between repos
      restrictions:
        - cannot_deploy: prod (requires CAB approval)
    
    ops_engineer:
      description: "Operations/SRE team"
      permissions:
        - read: all
        - deploy: all environments
        - rollback: all environments
        - approve: production deployments
        - access: monitoring, logs, alerts
    
    security_team:
      description: "Security team"
      permissions:
        - read: all
        - approve: security-sensitive changes
        - block: deployments with security issues
        - access: security scans, vulnerability reports
```

### Service-Level Access Control

```yaml
# Per-service RBAC
service_access:
  user-service:
    owners:
      - team: user-team
    write_access:
      - team: user-team
      - team: platform-team
    read_access:
      - all
    deploy_access:
      dev: [user-team]
      qa: [user-team, qa-team]
      uat: [release-managers]
      prod: [ops-team, release-managers]
    approve_access:
      - user-team-lead
      - platform-architect
      
  payment-service:
    owners:
      - team: payment-team
    write_access:
      - team: payment-team
    read_access:
      - team: payment-team
      - team: security-team
      - team: audit-team
    deploy_access:
      dev: [payment-team]
      qa: [payment-team, qa-team]
      uat: [release-managers]
      prod: [ops-team]  # Requires security approval
    approve_access:
      - payment-team-lead
      - security-team-lead
    additional_requirements:
      - security_review: required
      - pci_compliance: required
```

### Audit Trail Configuration

```yaml
# GitOps audit configuration
audit:
  git_tracking:
    enabled: true
    all_changes_in_git: true
    signed_commits: required
    
  deployment_logging:
    enabled: true
    log_destination: splunk
    retention_days: 365
    fields:
      - timestamp
      - actor
      - service
      - version
      - environment
      - status
      - approval_chain
      
  change_tracking:
    enabled: true
    platforms:
      - jira_integration: true
      - confluence_integration: true
    link_commits_to_tickets: required
    
  compliance:
    soc2:
      enabled: true
      evidence_collection: automatic
    pci_dss:
      enabled: true
      services: [payment-service]
    gdpr:
      enabled: true
      services: [user-service]
```

---

## Standardized Templates

### Principle #5: Reusable CI/CD Templates

```yaml
# ci-cd/templates/java-service-template.yaml
# Reusable template for Java microservices

parameters:
  - name: service_name
    required: true
  - name: java_version
    default: "17"
  - name: gradle_version
    default: "8.5"

stages:
  - template: build-stage
    parameters:
      language: java
      build_tool: gradle
      java_version: ${{ parameters.java_version }}
      
  - template: test-stage
    parameters:
      unit_tests: true
      integration_tests: true
      coverage_threshold: 80
      
  - template: security-stage
    parameters:
      sast: true
      dependency_check: true
      container_scan: true
      
  - template: docker-stage
    parameters:
      dockerfile: Dockerfile
      registry: company.jfrog.io
      
  - template: helm-stage
    parameters:
      chart_path: helm/
      
  - template: deploy-stage
    parameters:
      environments:
        - name: dev
          auto: true
          branch: develop
        - name: qa
          auto: true
          branch: release/*
        - name: uat
          auto: false
          requires_approval: true
        - name: prod
          auto: false
          requires_approval: true
          strategy: canary
```

### Dockerfile Templates

```dockerfile
# ci-cd/templates/Dockerfile.java
# Standard Java microservice Dockerfile

FROM eclipse-temurin:17-jdk-alpine AS builder

WORKDIR /app

# Copy gradle files for dependency caching
COPY build.gradle settings.gradle ./
COPY gradle ./gradle
COPY gradlew ./

# Download dependencies (cached layer)
RUN ./gradlew dependencies --no-daemon

# Copy source and build
COPY src ./src
RUN ./gradlew build -x test --no-daemon

# Runtime stage
FROM eclipse-temurin:17-jre-alpine

# Security: Run as non-root
RUN addgroup -g 1001 appgroup && \
    adduser -u 1001 -G appgroup -D appuser

WORKDIR /app

# Copy artifact
COPY --from=builder /app/build/libs/*.jar app.jar

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8080/actuator/health || exit 1

USER appuser

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
```

```dockerfile
# ci-cd/templates/Dockerfile.node
# Standard Node.js microservice Dockerfile

FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files for dependency caching
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source
COPY . .

# Build (for TypeScript/transpiled projects)
RUN npm run build

# Runtime stage
FROM node:20-alpine

# Security: Run as non-root
RUN addgroup -g 1001 appgroup && \
    adduser -u 1001 -G appgroup -D appuser

WORKDIR /app

# Copy from builder
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/health || exit 1

USER appuser

EXPOSE 3000

CMD ["node", "dist/index.js"]
```

### Helm Chart Template

```yaml
# ci-cd/templates/helm-chart-template/Chart.yaml
apiVersion: v2
name: {{ .ServiceName }}
description: Helm chart for {{ .ServiceName }}
type: application
version: {{ .ChartVersion }}
appVersion: {{ .AppVersion }}

dependencies:
  - name: common
    version: "1.x.x"
    repository: "oci://company.jfrog.io/helm-local"
```

```yaml
# ci-cd/templates/helm-chart-template/values.yaml
# Default values for microservice

replicaCount: 2

image:
  repository: company.jfrog.io/docker-release-local/{{ .ServiceName }}
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8080

ingress:
  enabled: true
  className: nginx
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: {{ .ServiceName }}.{{ .Environment }}.company.com
      paths:
        - path: /
          pathType: Prefix

resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

livenessProbe:
  httpGet:
    path: /actuator/health/liveness
    port: 8080
  initialDelaySeconds: 60
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /actuator/health/readiness
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 5

# Canary deployment settings
canary:
  enabled: false
  weight: 10
  
# Feature flags
featureFlags:
  provider: launchdarkly
  sdkKey: ""

# Observability
observability:
  tracing:
    enabled: true
    samplingRate: 0.1
  metrics:
    enabled: true
    path: /actuator/prometheus
```

---

## Complete Implementation

### Quick Start Guide

```bash
# 1. Clone the repository
git clone https://github.com/company/microservices-platform.git
cd microservices-platform

# 2. Start working on current release feature
git checkout develop
git pull origin develop
git checkout -b feature/BE-1234-new-api

# 3. Or start working on advance release feature
git checkout advance/3.0
git pull origin advance/3.0
git checkout -b feature/ADV-3.0-5678-future-feature

# 4. Make changes to your service
cd services/user-service
# ... develop ...

# 5. Commit with conventional commits
git add .
git commit -m "feat(user-service): add new authentication endpoint

- Added OAuth2 support
- Updated user model
- Added unit tests

Refs: BE-1234"

# 6. Push and create PR
git push -u origin feature/BE-1234-new-api
gh pr create --base develop --title "feat(user-service): add new authentication endpoint"

# 7. After approval, merge triggers pipeline
# - Build & test only user-service
# - Push to JFrog (docker-dev-local/user-service:x.x.x-abc123)
# - Deploy to dev environment
```

### Summary Table

| Aspect | Strategy |
|--------|----------|
| **Branching** | Trunk-based with advance release branches |
| **Advance Releases** | `advance/<version>` branches for future work |
| **Versioning** | Independent SemVer per service |
| **Pipeline Isolation** | Path-based triggers, one pipeline per service |
| **Artifacts** | JFrog with dev/rc/release repositories |
| **Promotion** | Build once, promote through environments |
| **Deployment** | Canary for production, rolling for others |
| **Feature Flags** | Progressive rollout, environment-specific |
| **RBAC** | Service-level + environment-level access |
| **Templates** | Reusable Dockerfiles, Helm charts, pipelines |

### Key Benefits

```yaml
benefits:
  faster_delivery:
    - "Build only changed services (80% CI time reduction)"
    - "Independent release cycles per service"
    - "Parallel team development"
    
  reduced_risk:
    - "Canary deployments catch issues early"
    - "Feature flags enable safe rollouts"
    - "Instant rollback with JFrog artifacts"
    
  better_governance:
    - "GitOps = Git is source of truth"
    - "Full audit trail"
    - "RBAC per service and environment"
    
  scalability:
    - "100+ developers can work independently"
    - "Advance releases prevent blocking"
    - "Standardized templates ensure consistency"
```

---

## Quick Reference

### Branch Commands

```bash
# Current release work
git checkout -b feature/BE-xxx develop
git checkout -b bugfix/BE-xxx develop

# Advance release work
git checkout -b feature/ADV-3.0-xxx advance/3.0

# Create release
git checkout -b release/2.5.0 develop

# Hotfix
git checkout -b hotfix/PROD-xxx master
```

### JFrog Commands

```bash
# Promote artifact
./ci-cd/scripts/jfrog-promote.sh user-service 2.3.1-rc.2 docker-rc-local docker-release-local

# Rollback
./ci-cd/scripts/rollback.sh user-service production 2.3.0
```

### Deployment Commands

```bash
# Deploy to environment
helm upgrade --install user-service \
  oci://company.jfrog.io/helm-local/user-service \
  --version 2.3.1 \
  -f services/user-service/helm/values-qa.yaml \
  -n qa

# Check rollout status
kubectl rollout status deployment/user-service -n production

# Rollback
kubectl rollout undo deployment/user-service -n production
```
