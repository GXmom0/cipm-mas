# 新疆棉田植保决策多智能体系统 - Git 初始化与提交
# 在 PowerShell 中执行：cd "D:\work产生的数据" ; powershell -ExecutionPolicy Bypass -File git_push.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Step 1: Git Init ===" -ForegroundColor Cyan
cd "D:\work产生的数据"

# 如果已有 .git 就清掉重来（因为之前 init 过但 add 失败）
if (Test-Path ".git") {
    Write-Host "Removing existing .git dir..."
    Remove-Item -Recurse -Force ".git"
}

git init
git branch -M main

Write-Host "`n=== Step 2: Add Files ===" -ForegroundColor Cyan
git add -A

Write-Host "`n=== Step 3: Commit ===" -ForegroundColor Cyan
git commit -m "feat: CIPM-MAS V1.1 + CI + 状态机 + 规则缺口 + README 标注

Core optimizations (2-day sprint):
- Add GitHub Actions CI (mock.cli --check + schema_export --check + pytest)
- Add prescription state machine hard guard (assert_transition)
- Add work_order state machine hard guard (assert_transition)
- Add prescription_guard.py (6 prerequisites pure function gate)
- Extend work_window.py with precipitation <=30% check
- Update README with 3-tier honesty labels (已实现/演示骨架/规划中)
- Update .gitignore to exclude large binaries and IDE caches

Test: 514 passed / 0 failed
Gates: mock.cli --check OK, schema_export --check OK"

Write-Host "`n=== Step 4: Create GitHub Repo ===" -ForegroundColor Cyan
$repoName = Read-Host "Enter GitHub repo name (e.g. cipm-mas)"
$owner = git config user.name
$repoUrl = "https://github.com/$owner/$repoName.git"

Write-Host "`nRepository URL will be: $repoUrl"
Write-Host "Please create the repo on GitHub first (or run: gh repo create $repoName --public)"
Write-Host "Then run: git remote add origin $repoUrl"
Write-Host "         git push -u origin main"

Write-Host "`n=== Done ===" -ForegroundColor Green
Write-Host "After push, tell me the repo URL and I'll update the CI badge!"
