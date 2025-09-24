# SSL Certificates Directory

This directory should contain your SSL certificates for the evaluation environment.

## Required Files

For the evaluation stack to work properly, you need:

- `wildcard.pucsr.edu.kh.crt` - The wildcard certificate file
- `wildcard.pucsr.edu.kh.key` - The private key file

## Certificate Installation

1. Obtain your wildcard certificate for `*.pucsr.edu.kh`
2. Place the certificate file as: `wildcard.pucsr.edu.kh.crt`  
3. Place the private key as: `wildcard.pucsr.edu.kh.key`
4. Ensure proper file permissions:
   ```bash
   chmod 644 wildcard.pucsr.edu.kh.crt
   chmod 600 wildcard.pucsr.edu.kh.key
   ```

## Development Environment

The development environment uses Let's Encrypt automatic certificates, so no manual certificate installation is required.

## Security Note

- Keep the private key file secure and never commit it to version control
- Regularly check certificate expiration dates
- Use proper file permissions to protect the private key