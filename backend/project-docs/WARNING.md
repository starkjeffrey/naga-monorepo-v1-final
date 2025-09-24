# 🚨 CRITICAL OPERATION WARNING 🚨

## READ THIS BEFORE ANY DATABASE OPERATION

**ABSOLUTE REQUIREMENT: FOLLOW EXACT ENVIRONMENT INSTRUCTIONS**

I must:

1. **Read your instructions more carefully**
2. **Follow them exactly as stated**
3. **Ask for clarification when uncertain** rather than making assumptions
4. **Pay attention to which environment you specify**

## Environment Protocol

**Environment Commands:**

- **MIGRATION**: `docker-compose.migration.yml` (REAL DATA - EXTREME CAUTION)
- **TEST/DEFAULT**: `docker-compose.local.yml` (SAFE FOR DEVELOPMENT)

**Critical Rules:**

- **MIGRATION database contains REAL LEGACY DATA** - treat with extreme caution
- **TEST/DEFAULT database is for development** - safe for testing and experimentation
- **ALWAYS use the EXACT environment specified** by the user
- **NEVER assume or change environments** without explicit permission
- **When in doubt, STOP and ASK** rather than making assumptions

## Before ANY Database Operation:

1. **READ** the user's environment specification carefully
2. **CONFIRM** which docker-compose file to use
3. **ASK** if uncertain about environment choice
4. **REMEMBER**: Migration data represents real institutional history

## If I Make an Environment Error:

- **IMMEDIATELY ACKNOWLEDGE** the mistake
- **STOP** any ongoing operations
- **ASSESS** potential damage to real data
- **FOLLOW** user's instructions for remediation

---

**Remember: The MIGRATION environment is sacred - it contains years of real institutional data that cannot be easily replaced.**
