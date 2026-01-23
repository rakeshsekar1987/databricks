# Microservice Branching Strategy for Large Teams

## Overview

This guide outlines the optimal Git branching strategy for **100+ developers** working on microservices with a promotion pipeline: **Dev → QA → UAT → Pre-Prod → Production**.

---

## Table of Contents

1. [Recommended Strategy: Scaled Trunk-Based Development](#recommended-strategy-scaled-trunk-based-development)
2. [Branch Structure](#branch-structure)
3. [Environment Mapping](#environment-mapping)
4. [Developer Workflow](#developer-workflow)
5. [Release Management](#release-management)
6. [Branch Protection Rules](#branch-protection-rules)
7. [Merge Strategies](#merge-strategies)
8. [CI/CD Integration](#cicd-integration)
9. [Alternative Strategies Comparison](#alternative-strategies-comparison)
10. [Best Practices for 100+ Developers](#best-practices-for-100-developers)

---

## Recommended Strategy: Scaled Trunk-Based Development

For 100+ developers working on microservices, **Scaled Trunk-Based Development with Release Branches** is the recommended approach.

### Why This Strategy?

| Challenge | Solution |
|-----------|----------|
| 100+ developers creating conflicts | Short-lived feature branches (< 2 days) |
| Multiple environments | Environment-mapped release branches |
| Parallel releases | Release branches per version |
| Hotfix requirements | Hotfix branches from release |
| Code review at scale | Pull request workflow |
| Continuous deployment | Automated promotion pipelines |

```
                                    ┌─────────────────────────────────────────────────────────────┐
                                    │                    BRANCH STRUCTURE                         │
                                    └─────────────────────────────────────────────────────────────┘

    Feature Branches (Short-lived: 1-2 days)
    ─────────────────────────────────────────
    feature/user-123-add-payment  ──────┐
    feature/user-456-fix-login    ────┐ │
    feature/user-789-new-api      ──┐ │ │
                                    │ │ │
                                    ▼ ▼ ▼
    ════════════════════════════════════════════════════════════════════════════════
                                   develop (main development)
    ════════════════════════════════════════════════════════════════════════════════
                                       │
                                       │ (Release cut)
                                       ▼
    ────────────────────────────────────────────────────────────────────────────────
                               release/v2.5.0 ──────────────────────────────────────►
    ────────────────────────────────────────────────────────────────────────────────
                                       │
                                       │ (After UAT approval)
                                       ▼
    ════════════════════════════════════════════════════════════════════════════════
                                     main (production)
    ════════════════════════════════════════════════════════════════════════════════
```

---

## Branch Structure

### Core Branches

| Branch | Purpose | Protected | Environment |
|--------|---------|-----------|-------------|
| `main` | Production-ready code | ✅ Heavily | Production |
| `develop` | Integration branch | ✅ Yes | Dev |
| `release/*` | Release candidates | ✅ Yes | QA → UAT → Pre-Prod |

### Supporting Branches

| Branch Pattern | Purpose | Lifetime | Created From |
|----------------|---------|----------|--------------|
| `feature/*` | New features | 1-3 days | `develop` |
| `bugfix/*` | Bug fixes | 1-2 days | `develop` |
| `hotfix/*` | Production fixes | Hours | `main` |
| `release/*` | Release preparation | Until deployed | `develop` |

### Branch Naming Conventions

```bash
# Feature branches
feature/<ticket-id>-<short-description>
feature/JIRA-1234-add-payment-gateway
feature/USER-567-implement-oauth

# Bugfix branches
bugfix/<ticket-id>-<short-description>
bugfix/JIRA-2345-fix-null-pointer

# Release branches
release/v<major>.<minor>.<patch>
release/v2.5.0
release/v2.5.1

# Hotfix branches
hotfix/<ticket-id>-<short-description>
hotfix/JIRA-9999-critical-security-fix
```

---

## Environment Mapping

### Branch-to-Environment Strategy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ENVIRONMENT PROMOTION FLOW                               │
└─────────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │     DEV      │    │      QA      │    │     UAT      │    │   PRE-PROD   │    │  PRODUCTION  │
  │              │    │              │    │              │    │              │    │              │
  │   develop    │───►│  release/*   │───►│  release/*   │───►│  release/*   │───►│    main      │
  │   branch     │    │   + QA tag   │    │  + UAT tag   │    │ + PP tag     │    │   branch     │
  └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │                   │                   │
        ▼                   ▼                   ▼                   ▼                   ▼
   Auto-deploy         Manual Gate         Manual Gate         Manual Gate         Manual Gate
   on merge            + Auto-deploy       + Auto-deploy       + Auto-deploy       + Auto-deploy
```

### Tagging Strategy for Environments

```bash
# Development (automatic on merge to develop)
# No tag needed - always latest develop

# QA Environment
git tag -a qa-v2.5.0-rc1 -m "Release candidate 1 for QA"
git push origin qa-v2.5.0-rc1

# UAT Environment  
git tag -a uat-v2.5.0-rc1 -m "Approved for UAT testing"
git push origin uat-v2.5.0-rc1

# Pre-Production Environment
git tag -a preprod-v2.5.0 -m "Pre-production validation"
git push origin preprod-v2.5.0

# Production Release
git tag -a v2.5.0 -m "Production release v2.5.0"
git push origin v2.5.0
```

### Environment Configuration

```yaml
# .github/environments.yaml
environments:
  dev:
    branch: develop
    auto_deploy: true
    approvers: []
    
  qa:
    branch: release/*
    tag_pattern: qa-*
    auto_deploy: true
    approvers:
      - qa-team
    
  uat:
    branch: release/*
    tag_pattern: uat-*
    auto_deploy: false
    approvers:
      - qa-lead
      - product-owner
    
  preprod:
    branch: release/*
    tag_pattern: preprod-*
    auto_deploy: false
    approvers:
      - tech-lead
      - release-manager
    
  production:
    branch: main
    tag_pattern: v*
    auto_deploy: false
    approvers:
      - release-manager
      - ops-team
    required_reviews: 2
```

---

## Developer Workflow

### Daily Development Flow

```bash
# 1. Start new feature
git checkout develop
git pull origin develop
git checkout -b feature/JIRA-1234-add-payment

# 2. Make changes with frequent commits
git add .
git commit -m "feat(payment): add stripe integration"

# 3. Keep branch updated (daily)
git fetch origin develop
git rebase origin/develop

# 4. Push and create PR
git push -u origin feature/JIRA-1234-add-payment
# Create Pull Request to develop

# 5. After PR approval and merge, delete branch
git checkout develop
git pull origin develop
git branch -d feature/JIRA-1234-add-payment
```

### Visual Workflow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DEVELOPER DAILY WORKFLOW                               │
└─────────────────────────────────────────────────────────────────────────────────┘

    Developer A                     Developer B                     Developer C
         │                               │                               │
         │ feature/add-payment           │ feature/fix-auth              │ feature/new-api
         │                               │                               │
         ▼                               ▼                               ▼
    ┌─────────┐                     ┌─────────┐                     ┌─────────┐
    │ Create  │                     │ Create  │                     │ Create  │
    │ Branch  │                     │ Branch  │                     │ Branch  │
    └────┬────┘                     └────┬────┘                     └────┬────┘
         │                               │                               │
         ▼                               ▼                               ▼
    ┌─────────┐                     ┌─────────┐                     ┌─────────┐
    │ Develop │                     │ Develop │                     │ Develop │
    │ & Test  │                     │ & Test  │                     │ & Test  │
    └────┬────┘                     └────┬────┘                     └────┬────┘
         │                               │                               │
         ▼                               ▼                               ▼
    ┌─────────┐                     ┌─────────┐                     ┌─────────┐
    │ Create  │                     │ Create  │                     │ Create  │
    │   PR    │                     │   PR    │                     │   PR    │
    └────┬────┘                     └────┬────┘                     └────┬────┘
         │                               │                               │
         │         ┌─────────────────────┼───────────────────────┐       │
         │         │                     │                       │       │
         ▼         ▼                     ▼                       ▼       ▼
    ═══════════════════════════════════════════════════════════════════════════
                                    develop
    ═══════════════════════════════════════════════════════════════════════════
```

### Pull Request Template

```markdown
## Description
<!-- Brief description of changes -->

## Type of Change
- [ ] Feature
- [ ] Bug Fix
- [ ] Refactoring
- [ ] Documentation

## Ticket Reference
JIRA-1234

## Checklist
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Code follows style guidelines
- [ ] Self-reviewed code

## Testing Instructions
<!-- How to test these changes -->

## Screenshots (if applicable)
<!-- Add screenshots for UI changes -->
```

---

## Release Management

### Release Process Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RELEASE LIFECYCLE                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

  Week 1-2: Development          Week 3: Stabilization          Week 4: Release
  ─────────────────────          ──────────────────────          ─────────────────
  
       develop                        release/v2.5.0                   main
          │                                │                             │
  ┌───────┴───────┐                        │                             │
  │ Features      │                        │                             │
  │ merged daily  │──── Release Cut ──────►│                             │
  │               │                        │                             │
  └───────────────┘                   ┌────┴────┐                        │
                                      │ QA      │                        │
                                      │ Testing │                        │
                                      └────┬────┘                        │
                                           │                             │
                                      ┌────┴────┐                        │
                                      │ UAT     │                        │
                                      │ Sign-off│                        │
                                      └────┬────┘                        │
                                           │                             │
                                      ┌────┴────┐                        │
                                      │Pre-Prod │                        │
                                      │ Validate│                        │
                                      └────┬────┘                        │
                                           │                             │
                                           └─────── Merge ──────────────►│
                                                                         │
                                                                    ┌────┴────┐
                                                                    │  v2.5.0 │
                                                                    │   Tag   │
                                                                    └─────────┘
```

### Release Branch Creation

```bash
# Create release branch from develop
git checkout develop
git pull origin develop
git checkout -b release/v2.5.0

# Push release branch
git push -u origin release/v2.5.0

# Create initial RC tag for QA
git tag -a v2.5.0-rc1 -m "Release candidate 1"
git push origin v2.5.0-rc1
```

### Hotfix Process

```bash
# Create hotfix from main
git checkout main
git pull origin main
git checkout -b hotfix/JIRA-9999-critical-fix

# Fix the issue
git add .
git commit -m "fix(critical): resolve security vulnerability"

# Create PR to main
git push -u origin hotfix/JIRA-9999-critical-fix

# After merge to main, also merge to develop and active release branches
git checkout develop
git pull origin develop
git merge main
git push origin develop

# If release branch exists
git checkout release/v2.5.0
git cherry-pick <hotfix-commit-hash>
git push origin release/v2.5.0
```

### Release Automation Script

```bash
#!/bin/bash
# scripts/create-release.sh

VERSION=$1
RELEASE_BRANCH="release/v${VERSION}"

if [ -z "$VERSION" ]; then
    echo "Usage: ./create-release.sh <version>"
    exit 1
fi

# Ensure we're on latest develop
git checkout develop
git pull origin develop

# Create release branch
git checkout -b "$RELEASE_BRANCH"

# Update version in package files
sed -i "s/version=.*/version=${VERSION}/" setup.py 2>/dev/null || true
sed -i "s/\"version\": \".*\"/\"version\": \"${VERSION}\"/" package.json 2>/dev/null || true

# Commit version bump
git add .
git commit -m "chore(release): bump version to ${VERSION}"

# Push release branch
git push -u origin "$RELEASE_BRANCH"

# Create initial RC tag
git tag -a "v${VERSION}-rc1" -m "Release candidate 1 for version ${VERSION}"
git push origin "v${VERSION}-rc1"

echo "Release branch $RELEASE_BRANCH created and pushed"
echo "RC tag v${VERSION}-rc1 created"
```

---

## Branch Protection Rules

### GitHub Branch Protection Configuration

```yaml
# Branch protection for 'main'
main:
  protection:
    required_status_checks:
      strict: true
      contexts:
        - "build"
        - "test-unit"
        - "test-integration"
        - "security-scan"
        - "sonarqube"
    required_pull_request_reviews:
      required_approving_review_count: 2
      dismiss_stale_reviews: true
      require_code_owner_reviews: true
      require_last_push_approval: true
    restrictions:
      users: []
      teams:
        - release-managers
    enforce_admins: true
    required_linear_history: true
    allow_force_pushes: false
    allow_deletions: false

# Branch protection for 'develop'
develop:
  protection:
    required_status_checks:
      strict: true
      contexts:
        - "build"
        - "test-unit"
        - "lint"
    required_pull_request_reviews:
      required_approving_review_count: 1
      dismiss_stale_reviews: true
    allow_force_pushes: false
    allow_deletions: false

# Branch protection for 'release/*'
release/*:
  protection:
    required_status_checks:
      strict: true
      contexts:
        - "build"
        - "test-unit"
        - "test-integration"
        - "test-e2e"
    required_pull_request_reviews:
      required_approving_review_count: 2
      require_code_owner_reviews: true
    restrictions:
      teams:
        - release-managers
        - qa-team
    allow_force_pushes: false
```

### CODEOWNERS File

```bash
# .github/CODEOWNERS

# Default owners for everything
* @platform-team

# Specific service ownership
/services/user-service/       @user-team
/services/payment-service/    @payment-team @security-team
/services/order-service/      @order-team
/services/notification/       @notification-team

# Infrastructure ownership
/infrastructure/              @devops-team @sre-team
/terraform/                   @devops-team

# CI/CD pipelines
/.github/                     @devops-team
/Jenkinsfile                  @devops-team

# Security-sensitive files
/security/                    @security-team
**/secrets/                   @security-team
*.pem                         @security-team
```

---

## Merge Strategies

### Recommended Merge Strategy by Branch Type

| Source → Target | Strategy | Rationale |
|-----------------|----------|-----------|
| feature/* → develop | Squash Merge | Clean history, one commit per feature |
| bugfix/* → develop | Squash Merge | Clean history |
| develop → release/* | Merge Commit | Preserve history for release |
| release/* → main | Merge Commit | Preserve release history |
| hotfix/* → main | Squash Merge | Clean hotfix tracking |
| main → develop | Merge Commit | Sync hotfixes to develop |

### Git Configuration for Teams

```bash
# .gitconfig recommended settings
[merge]
    ff = false                    # Always create merge commits for protected branches
    conflictstyle = diff3         # Show original in conflicts

[pull]
    rebase = true                 # Rebase local changes on pull

[branch]
    autosetuprebase = always      # Auto-setup rebase for new branches

[rebase]
    autoSquash = true             # Auto-squash fixup commits
    autoStash = true              # Auto-stash before rebase
```

### Squash Merge Commit Message Template

```bash
# Squash merge commit format
<type>(<scope>): <description> (#PR-number)

# Examples:
feat(payment): add Stripe payment integration (#1234)
fix(auth): resolve token refresh issue (#1235)
refactor(order): optimize database queries (#1236)
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/ci-cd.yaml
name: CI/CD Pipeline

on:
  push:
    branches: [develop, main, 'release/**']
  pull_request:
    branches: [develop, main, 'release/**']

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ============================================
  # BUILD & TEST (All branches)
  # ============================================
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Lint
        run: npm run lint
      
      - name: Unit Tests
        run: npm run test:unit -- --coverage
      
      - name: Build
        run: npm run build
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build-artifacts
          path: dist/

  # ============================================
  # INTEGRATION TESTS (develop, release/*, main)
  # ============================================
  integration-tests:
    needs: build-and-test
    if: github.ref == 'refs/heads/develop' || startsWith(github.ref, 'refs/heads/release/') || github.ref == 'refs/heads/main'
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
      - name: Run Integration Tests
        run: npm run test:integration

  # ============================================
  # SECURITY SCAN
  # ============================================
  security-scan:
    needs: build-and-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
      
      - name: Run SAST
        uses: github/codeql-action/analyze@v2

  # ============================================
  # DEPLOY TO DEV (develop branch only)
  # ============================================
  deploy-dev:
    needs: [build-and-test, integration-tests]
    if: github.ref == 'refs/heads/develop' && github.event_name == 'push'
    runs-on: ubuntu-latest
    environment: development
    steps:
      - name: Deploy to Dev
        run: |
          echo "Deploying to development environment"
          # kubectl apply -f k8s/dev/

  # ============================================
  # DEPLOY TO QA (release/* branches)
  # ============================================
  deploy-qa:
    needs: [build-and-test, integration-tests, security-scan]
    if: startsWith(github.ref, 'refs/heads/release/') && github.event_name == 'push'
    runs-on: ubuntu-latest
    environment: qa
    steps:
      - name: Deploy to QA
        run: |
          echo "Deploying to QA environment"
          # kubectl apply -f k8s/qa/

  # ============================================
  # DEPLOY TO UAT (requires approval)
  # ============================================
  deploy-uat:
    needs: deploy-qa
    if: startsWith(github.ref, 'refs/heads/release/')
    runs-on: ubuntu-latest
    environment: 
      name: uat
      url: https://uat.example.com
    steps:
      - name: Deploy to UAT
        run: |
          echo "Deploying to UAT environment"
          # kubectl apply -f k8s/uat/

  # ============================================
  # DEPLOY TO PRE-PROD (requires approval)
  # ============================================
  deploy-preprod:
    needs: deploy-uat
    if: startsWith(github.ref, 'refs/heads/release/')
    runs-on: ubuntu-latest
    environment:
      name: preprod
      url: https://preprod.example.com
    steps:
      - name: Deploy to Pre-Prod
        run: |
          echo "Deploying to Pre-Production environment"
          # kubectl apply -f k8s/preprod/

  # ============================================
  # DEPLOY TO PRODUCTION (main branch, requires approval)
  # ============================================
  deploy-production:
    needs: [build-and-test, integration-tests, security-scan]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - name: Deploy to Production
        run: |
          echo "Deploying to Production environment"
          # kubectl apply -f k8s/production/
```

### Environment Promotion Pipeline

```yaml
# .github/workflows/promote-release.yaml
name: Promote Release

on:
  workflow_dispatch:
    inputs:
      release_branch:
        description: 'Release branch (e.g., release/v2.5.0)'
        required: true
      target_environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - qa
          - uat
          - preprod
          - production

jobs:
  promote:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.target_environment }}
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.inputs.release_branch }}
      
      - name: Validate release branch
        run: |
          if [[ ! "${{ github.event.inputs.release_branch }}" =~ ^release/v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Invalid release branch format"
            exit 1
          fi
      
      - name: Create environment tag
        run: |
          VERSION=$(echo "${{ github.event.inputs.release_branch }}" | sed 's/release\///')
          ENV="${{ github.event.inputs.target_environment }}"
          TAG="${ENV}-${VERSION}"
          
          git tag -a "$TAG" -m "Promoted to ${ENV}"
          git push origin "$TAG"
      
      - name: Deploy to ${{ github.event.inputs.target_environment }}
        run: |
          echo "Deploying to ${{ github.event.inputs.target_environment }}"
          # Add deployment commands here
```

---

## Alternative Strategies Comparison

### Strategy Comparison Matrix

| Strategy | Team Size | Release Frequency | Complexity | Best For |
|----------|-----------|-------------------|------------|----------|
| **Trunk-Based (Scaled)** | 50-200+ | Daily/Weekly | Medium | Large teams, CI/CD mature |
| **GitFlow** | 10-50 | Monthly | High | Scheduled releases |
| **GitHub Flow** | 5-30 | Continuous | Low | Small teams, SaaS |
| **GitLab Flow** | 20-100 | Weekly | Medium | Environment-based releases |
| **Release Flow** | 50-500 | Scheduled | Medium | Large enterprise |

### GitFlow (Alternative)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              GITFLOW STRUCTURE                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

    hotfix─────────────────────────────────────────────────────────►
         \                                                         /
          \                                                       /
    main ══════════════════════════════════════════════════════════════════════
              \                                               /
               \                                             /
    release ────────────────────────────────────────────────►
                  \                                       /
                   \                                     /
    develop ═══════════════════════════════════════════════════════════════════
               /        /          \         \
              /        /            \         \
    feature ─►  feature ─►     feature ─►  feature ─►
```

**Pros**: Clear separation, good for scheduled releases
**Cons**: Complex, long-lived branches cause merge conflicts

### GitHub Flow (Alternative for Smaller Teams)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            GITHUB FLOW (SIMPLE)                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

    feature/add-auth ────────┐
                             │
    feature/fix-bug ───────┐ │
                           │ │
    feature/new-api ─────┐ │ │
                         │ │ │
                         ▼ ▼ ▼
    main ════════════════════════════════════════════════════════════════════════
                              │
                              ▼
                         Deploy to all
                         environments
```

**Pros**: Simple, fast deployment
**Cons**: No environment staging, risky for large teams

---

## Best Practices for 100+ Developers

### 1. Team Organization

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           TEAM STRUCTURE (100+ devs)                             │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │ Release Manager │
                              │   (1-2 people)  │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
              ┌─────┴─────┐      ┌─────┴─────┐      ┌─────┴─────┐
              │  Domain A │      │  Domain B │      │  Domain C │
              │  (3-4     │      │  (3-4     │      │  (3-4     │
              │   teams)  │      │   teams)  │      │   teams)  │
              └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
                    │                  │                  │
         ┌──────────┼──────────┐       │         ┌────────┼────────┐
         │          │          │       │         │        │        │
      ┌──┴──┐   ┌──┴──┐   ┌──┴──┐  ┌──┴──┐   ┌──┴──┐  ┌──┴──┐  ┌──┴──┐
      │Team1│   │Team2│   │Team3│  │Team4│   │Team5│  │Team6│  │Team7│
      │8 dev│   │8 dev│   │8 dev│  │8 dev│   │8 dev│  │8 dev│  │8 dev│
      └─────┘   └─────┘   └─────┘  └─────┘   └─────┘  └─────┘  └─────┘
```

### 2. Repository Strategy for Microservices

```
Option A: Mono-Repo (Recommended for tight coupling)
────────────────────────────────────────────────────
microservices-platform/
├── services/
│   ├── user-service/
│   ├── order-service/
│   └── payment-service/
├── shared/
│   ├── common-lib/
│   └── api-contracts/
└── infrastructure/

Benefits:
- Atomic changes across services
- Shared tooling and CI/CD
- Easier dependency management

Option B: Multi-Repo (Recommended for independent teams)
────────────────────────────────────────────────────────
user-service/           (Team 1)
order-service/          (Team 2)
payment-service/        (Team 3)
shared-contracts/       (Platform team)
infrastructure/         (DevOps team)

Benefits:
- Independent deployment cycles
- Clear ownership boundaries
- Smaller, focused repositories
```

### 3. Code Review Guidelines

```yaml
# Review requirements by change size
review_policy:
  small_change:  # < 50 lines
    reviewers: 1
    approval_timeout: 4h
    
  medium_change:  # 50-200 lines
    reviewers: 2
    approval_timeout: 8h
    
  large_change:  # 200-500 lines
    reviewers: 2
    require_senior: true
    approval_timeout: 24h
    
  breaking_change:  # > 500 lines or API changes
    reviewers: 3
    require_architect: true
    require_security_review: true
    approval_timeout: 48h
```

### 4. Feature Flag Integration

```python
# Use feature flags for long-running features
from feature_flags import FeatureFlag

class PaymentService:
    def process_payment(self, order):
        if FeatureFlag.is_enabled("new_payment_flow", user=order.user):
            return self.new_payment_flow(order)
        else:
            return self.legacy_payment_flow(order)
```

### 5. Communication Channels

```yaml
# Slack/Teams channels for coordination
channels:
  - name: "#releases"
    purpose: Release announcements and coordination
    notify_on:
      - release_branch_created
      - deployment_to_production
      - hotfix_deployed
    
  - name: "#dev-{team-name}"
    purpose: Team-specific development discussions
    
  - name: "#merge-conflicts"
    purpose: Request help with merge conflicts
    
  - name: "#ci-cd-alerts"
    purpose: Pipeline failures and issues
```

### 6. Metrics to Track

```yaml
# Key metrics for branching strategy health
metrics:
  branch_lifespan:
    target: "< 2 days for features"
    alert_threshold: "5 days"
    
  merge_conflict_rate:
    target: "< 5% of PRs"
    alert_threshold: "15%"
    
  pr_review_time:
    target: "< 4 hours"
    alert_threshold: "24 hours"
    
  deployment_frequency:
    target: "Daily to dev, Weekly to prod"
    
  lead_time:
    target: "< 1 week from commit to production"
    
  rollback_rate:
    target: "< 2% of deployments"
    alert_threshold: "5%"
```

---

## Quick Reference

### Daily Commands Cheat Sheet

```bash
# Start new feature
git checkout develop && git pull && git checkout -b feature/JIRA-XXX-description

# Update feature branch
git fetch origin develop && git rebase origin/develop

# Create PR (using GitHub CLI)
gh pr create --base develop --title "feat: description" --body "JIRA-XXX"

# Create release
./scripts/create-release.sh 2.5.0

# Hotfix
git checkout main && git pull && git checkout -b hotfix/JIRA-XXX-critical-fix

# Promote to environment
git tag -a qa-v2.5.0-rc1 -m "QA release" && git push origin qa-v2.5.0-rc1
```

### Branch Lifecycle Summary

| Branch Type | Created From | Merges To | Lifespan |
|-------------|--------------|-----------|----------|
| feature/* | develop | develop | 1-3 days |
| bugfix/* | develop | develop | 1-2 days |
| release/* | develop | main, develop | 1-2 weeks |
| hotfix/* | main | main, develop | Hours |

---

## Summary

For **100+ developers** working on microservices with **Dev → QA → UAT → Pre-Prod → Production** pipeline:

1. **Use Scaled Trunk-Based Development** with release branches
2. **Keep feature branches short-lived** (1-3 days max)
3. **Map environments to tags/branches**: develop→Dev, release/*→QA/UAT/Pre-Prod, main→Production
4. **Enforce branch protection** with required reviews and CI checks
5. **Use squash merges** for features, regular merges for releases
6. **Automate everything** with CI/CD pipelines
7. **Track metrics** to identify bottlenecks

This strategy balances agility with stability, enabling rapid development while maintaining quality gates for production releases.
