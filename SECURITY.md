# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in StarDiscover, please report it responsibly:

1. **Do not** open a public issue
2. Email the maintainers directly or use GitHub's private vulnerability reporting
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue.

## Security Considerations

### Authentication & Secrets

- **SECRET_KEY**: Used for session encryption. Generate a strong random key:
  ```bash
  openssl rand -base64 32
  ```
- **GitHub OAuth**: Client secrets should never be committed to version control
- **Access Tokens**: User access tokens are stored in the database and used for GitHub API calls

### Data Storage

- SQLite database stores user information and access tokens
- The `data/` directory should be properly secured on the host system
- Consider encrypting the database at rest for production deployments

### Network Security

- Deploy behind a reverse proxy (nginx, Traefik) with HTTPS
- Use proper CORS settings in production
- Consider network isolation for the Redis container

### Best Practices

1. **Keep dependencies updated**: Regularly update Python packages
   ```bash
   pip install --upgrade -r requirements.txt
   ```

2. **Use HTTPS in production**: Update `GITHUB_REDIRECT_URI` to use HTTPS

3. **Secure Redis**: In production, enable Redis authentication

4. **Database backups**: Regularly backup the SQLite database

5. **Log monitoring**: Monitor application logs for suspicious activity

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |

## Security Updates

Security updates will be released as soon as possible after a vulnerability is confirmed. Watch the repository for release notifications.
