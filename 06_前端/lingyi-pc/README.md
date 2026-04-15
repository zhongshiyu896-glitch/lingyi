# lingyi-pc Frontend

## Fixed Runtime Versions
- Node: `22.22.1`
- npm: `10.9.4`

This project pins runtime versions with:
- `.nvmrc`
- `.npmrc` (`engine-strict=true`, `package-lock=true`)
- `package.json` (`packageManager`, `engines`)

## Local Verification
Run in `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`:

```bash
node -v
npm -v
npm ci
npm run test:production-contracts
npm run check:production-contracts
npm run verify
npm run typecheck
npm run build
npm audit --audit-level=high
```

## CI Hard Gate
- Workflow name: `Frontend Verify Hard Gate`
- Job name: `lingyi-pc-verify`
- Suggested required check name:
  `Frontend Verify Hard Gate / lingyi-pc-verify`
