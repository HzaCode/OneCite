import requests

print("📊 获取 OneCite 项目数据...\n")

# GitHub API
github_url = "https://api.github.com/repos/HzaCode/OneCite"
try:
    response = requests.get(github_url)
    repo_data = response.json()
    stars = repo_data.get('stargazers_count', 0)
    forks = repo_data.get('forks_count', 0)
    watchers = repo_data.get('watchers_count', 0)
    print(f"⭐ GitHub Stars: {stars}")
    print(f"🔱 Forks: {forks}")
    print(f"👁️  Watchers: {watchers}")
except Exception as e:
    print(f"GitHub API 错误: {e}")

# PyPI API
print("\n📦 PyPI 数据:")
pypi_url = "https://pypi.org/pypi/onecite/json"
try:
    response = requests.get(pypi_url)
    pypi_data = response.json()
    version = pypi_data['info']['version']
    print(f"   版本: {version}")
    print(f"   许可证: {pypi_data['info']['license']}")
    print(f"   主页: {pypi_data['info']['home_page']}")
except Exception as e:
    print(f"PyPI API 错误: {e}")

# PePy 下载统计
print("\n📈 下载统计（可从 https://pepy.tech/project/onecite 查看）")




