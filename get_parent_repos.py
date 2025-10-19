import requests
import json

# 需要查询的仓库列表（排除 awesome-LaTeX）
target_repos = [
    "awesome-research",
    "awesome-python",
    "awesome-cli-apps",
    "awesome-markdown",
    "awesome-python-chemistry",
    "awesome-healthcare",
    "awesome-code-review",
    "awesome-ci"
]

username = "HzaCode"
headers = {'Accept': 'application/vnd.github.v3+json'}

print("🔍 正在查询上游仓库信息...\n")
print("=" * 100)

parent_repos = []

for repo_name in target_repos:
    api_url = f"https://api.github.com/repos/{username}/{repo_name}"
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        repo_data = response.json()
        
        parent = repo_data.get('parent')
        if parent:
            parent_info = {
                'fork_name': repo_name,
                'fork_url': repo_data['html_url'],
                'parent_full_name': parent['full_name'],
                'parent_url': parent['html_url'],
                'parent_stars': parent['stargazers_count'],
                'parent_description': parent.get('description', 'N/A'),
                'parent_language': parent.get('language', 'N/A'),
                'parent_topics': parent.get('topics', [])
            }
            parent_repos.append(parent_info)
            
            print(f"\n✅ {repo_name}")
            print(f"   你的 Fork: {repo_data['html_url']}")
            print(f"   上游仓库: {parent['full_name']}")
            print(f"   上游链接: {parent['html_url']}")
            print(f"   Stars: ⭐ {parent['stargazers_count']:,}")
            print(f"   描述: {parent.get('description', 'N/A')}")
            if parent.get('topics'):
                print(f"   标签: {', '.join(parent.get('topics', []))}")
        else:
            print(f"\n⚠️  {repo_name} - 未找到上游仓库信息")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ {repo_name} - 请求失败: {e}")
    except Exception as e:
        print(f"\n❌ {repo_name} - 发生错误: {e}")

print("\n" + "=" * 100)
print(f"\n📋 汇总信息：")
print(f"\n共找到 {len(parent_repos)} 个上游仓库可以提交 PR：\n")

# 按 Stars 数量排序
parent_repos_sorted = sorted(parent_repos, key=lambda x: x['parent_stars'], reverse=True)

for i, repo in enumerate(parent_repos_sorted, 1):
    print(f"{i}. {repo['parent_full_name']} (⭐ {repo['parent_stars']:,})")
    print(f"   {repo['parent_url']}")
    print()

# 生成一个可复制的列表
print("\n" + "=" * 100)
print("\n📝 可直接访问的上游仓库列表：\n")
for repo in parent_repos_sorted:
    print(f"- [ ] {repo['parent_full_name']} - {repo['parent_url']}")




