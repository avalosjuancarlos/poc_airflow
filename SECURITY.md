# 🔐 Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in this project, please report it by creating a private security advisory on GitHub or contacting the maintainers directly.

**Please do NOT create a public issue for security vulnerabilities.**

---

## Security Best Practices

### 1. **Environment Variables & Secrets Management**

#### ✅ **DO:**
- Keep `.env` file in `.gitignore` (already configured)
- Use `env.template` with placeholder values prefixed with `CHANGE_ME_`
- Store real credentials only in local `.env` file (never commit)
- Use secret management tools in production (AWS Secrets Manager, HashiCorp Vault, etc.)

#### ❌ **DON'T:**
- Never commit `.env` files with real credentials
- Never hardcode passwords, API keys, or tokens in source code
- Never push realistic-looking passwords in templates (triggers GitGuardian)

### 2. **Credential Placeholders**

All passwords in `env.template` use the `CHANGE_ME_` prefix to clearly indicate they are placeholders:

```bash
# ❌ BAD (looks like real credential)
DEV_WAREHOUSE_PASSWORD=warehouse_pass

# ✅ GOOD (obvious placeholder)
DEV_WAREHOUSE_PASSWORD=CHANGE_ME_dev_warehouse_password
```

### 3. **Database Security**

#### Development Environment
- Development PostgreSQL runs as non-root user (UID 999)
- Uses `md5` authentication instead of `trust` for local connections
- Dedicated database for warehouse (separate from Airflow metadata)

#### Production Environment
- Use IAM authentication for Redshift when possible
- Rotate credentials regularly
- Use VPC and security groups to restrict access
- Enable SSL/TLS for all database connections

### 4. **Airflow Security**

- Change default Airflow admin credentials (in `.env`)
- Use Fernet key encryption for connections and variables
- Enable RBAC (Role-Based Access Control)
- Restrict webserver access via firewall/VPN

### 5. **CI/CD Security**

- GitHub Actions uses secrets for sensitive data
- Never log sensitive information
- Use minimal permissions for service accounts
- Regularly rotate CI/CD credentials

---

## Security Alerts

### GitGuardian Integration

This repository is monitored by GitGuardian for exposed secrets. If you receive an alert:

1. **Verify** if the detected secret is real or a false positive
2. **If false positive**: Update placeholder to use `CHANGE_ME_` prefix
3. **If real secret**:
   - Immediately rotate the exposed credential
   - Remove from git history using `git filter-repo` or BFG Repo-Cleaner
   - Update `.gitignore` to prevent future exposure
   - Notify all team members

### Recent Alerts (Resolved)

- **Nov 12, 2025**: Generic Database Assignment in `env.template`
  - **Status**: ✅ Resolved
  - **Action**: Updated all password placeholders to use `CHANGE_ME_` prefix
  - **Verified**: `.env` with real credentials was never committed

---

## Dependency Security

- Use `pip-audit` or `safety` to scan for vulnerable dependencies
- Keep dependencies updated (automated via Dependabot)
- Review security advisories for Airflow and related packages

---

## Logging Security

- Never log passwords, tokens, or sensitive data
- Use log masking in `warehouse_config.py` (password replaced with `****`)
- Structured logging includes context but excludes secrets

---

## Contact

For security concerns, contact: [Your contact information]

---

## Acknowledgments

Security scanning provided by:
- **GitGuardian**: Secret detection and monitoring
- **GitHub**: Dependabot security updates

