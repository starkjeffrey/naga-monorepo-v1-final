# Manual Key File Copy Required

The wildcard certificate has been copied successfully, but the private key requires manual copying due to permission restrictions.

## Required Action

Run this command to copy the private key:

```bash
sudo cp /home/ommae/certs/star_pucsr_edu_kh.key /home/ommae/Projects/naga-monorepo/backend/compose/traefik/certs/wildcard.pucsr.edu.kh.key
```

Then set proper permissions:

```bash
sudo chown ommae:ommae /home/ommae/Projects/naga-monorepo/backend/compose/traefik/certs/wildcard.pucsr.edu.kh.key
chmod 600 /home/ommae/Projects/naga-monorepo/backend/compose/traefik/certs/wildcard.pucsr.edu.kh.key
```

## Verification

After copying, verify the files exist:

```bash
ls -la /home/ommae/Projects/naga-monorepo/backend/compose/traefik/certs/
```

You should see:
- `wildcard.pucsr.edu.kh.crt` (certificate)
- `wildcard.pucsr.edu.kh.key` (private key)

## Security Note

The private key file should have restrictive permissions (600) and never be committed to version control.