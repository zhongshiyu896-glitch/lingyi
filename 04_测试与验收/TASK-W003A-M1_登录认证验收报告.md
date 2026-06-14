# TASK-W003A-M1 登录认证验收报告

- 更新时间：2026-06-14 09:55 CST+8
- 范围：M1-S1 至 M1-S4，ERPNext 代理登录、生产登录页、路由守卫、会话级短 TTL 缓存、production 配置门。
- 结论：本地实现与自测 gate 通过；真实 ERPNext 账号登录与按钮权限抽验仍需用户执行，未进入 M2。

## 实现摘要

1. `LoginPage.vue` 增加密码字段、错误态、loading/disabled、redirect 回跳；production mode 隐藏 dev 角色下拉。
2. `/api/auth/login` 在 dev-auth 开启时保留本地 profile 登录；其余环境 server-side 调 ERPNext `/api/method/login`，成功回种 `sid` cookie，失败 401/403/503 fail-closed。
3. `/api/auth/me` 走 `get_current_user` 会话级短 TTL 缓存：key 使用 ERPNext `sid` / 本地会话 token，默认 45s、上限 60s，命中跳过 ERPNext 调用；失败不缓存，登出清理对应缓存与 cookie。
4. 配置门保持：`APP_ENV=production` 要求 `LINGYI_PERMISSION_SOURCE=erpnext`；dev-auth 默认关闭；主 app 不挂载 `/api/local-dev/*`。

## 自测结果

- `npm run verify`：PASS。
- `./.venv/bin/python -m pytest tests/test_auth_session.py tests/test_auth_actions.py tests/test_env.py tests/test_local_dev_asgi_contract.py -q`：24 passed。
- `./.venv/bin/python -m pytest tests/test_auth_session.py tests/test_env.py -q`：14 passed；断言同一 `sid` TTL 内第二次 `/api/auth/me` 不再打 ERPNext，TTL 过期或 logout 后重新解析。
- `node 04_测试与验收/测试证据/W003A_M1_erpnext_login/e2e_erpnext_login_flow.mjs`：PASS。

## 浏览器证据

- `04_测试与验收/测试证据/W003A_M1_erpnext_login/01_unauth_redirect_to_login.png`
- `04_测试与验收/测试证据/W003A_M1_erpnext_login/02_login_error_fail_closed.png`
- `04_测试与验收/测试证据/W003A_M1_erpnext_login/03_login_redirect_success.png`
- `04_测试与验收/测试证据/W003A_M1_erpnext_login/04_logout_returns_to_login.png`
- `04_测试与验收/测试证据/W003A_M1_erpnext_login/05_session_expired_redirect.png`
- `04_测试与验收/测试证据/W003A_M1_erpnext_login/e2e_summary.json`

## 未释放项

- 真实 ERPNext 生产账号、真实生产部署、PR/merge/tag/release 仍为 HUMAN_ONLY。
- M2 BOM 不启动，等待用户用真实 ERPNext 账号完成登录走通与按钮权限抽验。
