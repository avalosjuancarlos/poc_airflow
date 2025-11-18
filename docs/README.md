# 📚 Documentation Index

Welcome to the Apache Airflow Market Data Pipeline documentation! This guide will help you find the information you need.

## 📖 About This Documentation

This documentation is organized by audience and use case to help you quickly find what you need.

---

## 🚦 Getting Started

Perfect for new users and first-time setup.

| Document | Description | Status |
|----------|-------------|--------|
| **[Installation Guide](getting-started/installation.md)** | Complete installation and setup instructions | ✅ Available |
| **[Quick Start Tutorial](getting-started/quick-start.md)** | Get your first DAG running in 5 minutes | ✅ Available |
| **Configuration** → See [User Guide](user-guide/configuration.md) | Environment and configuration setup | ✅ Available |

---

## 👤 User Guide

For DAG users and data engineers working with the pipelines.

| Document | Description | Status |
|----------|-------------|--------|
| **[Market Data DAG](user-guide/market-data-dag.md)** | Complete guide to the Yahoo Finance DAG | ✅ Available |
| **[Data Warehouse Guide](user-guide/data-warehouse.md)** | Multi-environment warehouse integration | ✅ Available |
| **[Dashboard Guide](user-guide/dashboard.md)** | Interactive web dashboard with Streamlit | ✅ Available |
| **[Configuration Options](user-guide/configuration.md)** | All configurable parameters and variables | ✅ Available |
| **[Airflow Variables Guide](user-guide/airflow-variables.md)** | Working with Airflow Variables | ✅ Available |
| **[Logging Guide](user-guide/logging.md)** | Understanding and using the logging system | ✅ Available |

---

## 👨‍💻 Developer Guide

For developers contributing to or extending the codebase.

| Document | Description | Status |
|----------|-------------|--------|
| **[Architecture Overview](architecture/overview.md)** | Complete system architecture and design decisions | ✅ Available |
| **[Testing Guide](developer-guide/testing.md)** | Running and writing tests (197 tests, 92% coverage) | ✅ Available |
| **[API Reference](developer-guide/api-reference.md)** | Complete module and function documentation | ✅ Available |
| **[Code Style Guide](developer-guide/code-style.md)** | Coding standards and conventions | ✅ Available |
| **[Contributing Guide](developer-guide/contributing.md)** | How to contribute to the project | ✅ Available |

---

## ⚙️ Operations Guide

For DevOps engineers and system administrators.

| Document | Description | Status |
|----------|-------------|--------|
| **[Deployment Guide](operations/deployment.md)** | Production deployment (Docker, AWS, K8s) | ✅ Available |
| **[Monitoring Guide](operations/monitoring.md)** | Observability with Prometheus, Grafana, Datadog | ✅ Available |
| **[Troubleshooting Guide](operations/troubleshooting.md)** | Common issues and solutions | ✅ Available |
| **[Migration Guide](operations/migration-guide.md)** | Environment and version migration | ✅ Available |
| **[Performance Tuning](operations/performance-tuning.md)** | Optimization and scaling guide | ✅ Available |
| **Security Guide** → See [SECURITY.md](SECURITY.md) | Security best practices | ✅ Available |

---

## 📖 Reference Documentation

Quick reference materials and cheat sheets.

| Document | Description | Status |
|----------|-------------|--------|
| **[Environment Variables](reference/environment-variables.md)** | Complete reference for all env vars | ✅ Available |
| **[CLI Commands](reference/cli-commands.md)** | Comprehensive Airflow CLI reference | ✅ Available |
| **[FAQs](reference/faq.md)** | Frequently asked questions | ✅ Available |
| **Docker Compose** → See main [README](../README.md#-architecture) | Service configurations and details | ✅ Available |

---

## 🗂️ Legacy Documentation

Documentation from previous versions or being phased out.

| Document | Status | Replacement |
|----------|--------|-------------|
| `CONFIGURATION.md` | ✅ Active | Moved to [user-guide/configuration.md](user-guide/configuration.md) |
| `TESTING_GUIDE.md` | ✅ Active | Moved to [developer-guide/testing.md](developer-guide/testing.md) |
| `LOGGING_GUIDE.md` | ✅ Active | Moved to [user-guide/logging.md](user-guide/logging.md) |
| `AIRFLOW_VARIABLES_GUIDE.md` | ✅ Active | Moved to [user-guide/airflow-variables.md](user-guide/airflow-variables.md) |
| `REFACTOR_SUMMARY.md` | 📝 Archive | Technical history document |
| `VARIABLES_ANALYSIS.md` | 📝 Archive | Technical history document |
| `VERIFICATION.md` | ⚠️ Obsolete | No longer needed (initial setup verification) |

---

## 🔍 Finding What You Need

### By Task

| I want to... | Go to... |
|-------------|----------|
| Install Airflow for the first time | [Installation Guide](getting-started/installation.md) ✅ |
| Run my first DAG | [Market Data DAG Guide](user-guide/market-data-dag.md) ✅ |
| Configure market data parameters | [Configuration Guide](user-guide/configuration.md) ✅ |
| Understand the logging system | [Logging Guide](user-guide/logging.md) ✅ |
| Write tests for my DAG | [Testing Guide](developer-guide/testing.md) ✅ |
| Fix a problem | [Main README Troubleshooting](../README.md#-troubleshooting) ✅ |
| Use Airflow Variables | [Airflow Variables Guide](user-guide/airflow-variables.md) ✅ |

### By Role

| Role | Recommended Reading |
|------|-------------------|
| **New User** | [Installation](getting-started/installation.md) → [Market Data DAG](user-guide/market-data-dag.md) ✅ |
| **Data Engineer** | [Configuration](user-guide/configuration.md) → [Airflow Variables](user-guide/airflow-variables.md) → [Logging](user-guide/logging.md) ✅ |
| **Developer** | [Testing](developer-guide/testing.md) → Main README ✅ |
| **DevOps/SRE** | [Installation](getting-started/installation.md) → [Testing](developer-guide/testing.md) ✅ |

---

## 📊 Documentation Status

| Category | Available | Coming Soon | Total |
|----------|-----------|-------------|-------|
| Getting Started | 3 | 0 | 3 |
| User Guide | 6 | 0 | 6 |
| Developer Guide | 5 | 0 | 5 |
| Operations | 7 | 0 | 7 |
| Reference | 3 | 0 | 3 |
| **Total** | **24** | **0** | **24** |

**Current Completion**: 100% (24/24 documents) ✅

**Legend**: ✅ Available | 🔜 Coming Soon

---

## 🤝 Contributing to Documentation

Found a typo or want to improve the docs?

1. Documentation is written in Markdown
2. Keep style consistent with existing docs
3. Submit a Pull Request with your changes
4. All documentation goes through review

See the main [README](../README.md#-contributing) for contribution guidelines.

---

## 📞 Getting Help

- 🐛 [Report an Issue](https://github.com/avalosjuancarlos/poc_airflow/issues)
- 💬 [Discussions](https://github.com/avalosjuancarlos/poc_airflow/discussions)
- 📧 Email: support@example.com

---

## 🔄 Recent Updates

| Date | Document | Change |
|------|----------|--------|
| 2025-11-12 | **All** | **Documentation 100% Complete (23/23 documents)** 🎉 |
| 2025-11-12 | [API Reference](developer-guide/api-reference.md) | Complete API documentation added |
| 2025-11-12 | [FAQs](reference/faq.md) | 50+ frequently asked questions |
| 2025-11-12 | [Migration Guide](operations/migration-guide.md) | Environment migration procedures |
| 2025-11-12 | [Performance Tuning](operations/performance-tuning.md) | Optimization guide |
| 2025-11-12 | [Quick Start](getting-started/quick-start.md) | 5-minute setup guide |
| 2025-11-12 | [Architecture](architecture/overview.md) | Complete system architecture |
| 2025-11-12 | [Deployment](operations/deployment.md) | Production deployment |
| 2025-11-12 | [Monitoring](operations/monitoring.md) | Observability setup |
| 2025-11-12 | [Data Warehouse](user-guide/data-warehouse.md) | Warehouse integration |

---

<div align="center">

**[⬆ Back to Main README](../README.md)**

</div>

