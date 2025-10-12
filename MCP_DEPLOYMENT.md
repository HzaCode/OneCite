# OneCite MCP Server 部署指南

## 📦 安装

```bash
pip install onecite
```

## 🚀 使用方法

### 方法1：在MCP desktop client中使用

1. **安装OneCite**
```bash
pip install onecite
```

2. **配置MCP desktop client**

编辑MCP desktop client配置文件：
- **macOS**: `~/Library/Application Support/MCP client/claude_desktop_config.json`
- **Windows**: `%APPDATA%\MCP client\claude_desktop_config.json`

添加以下配置：
```json
{
  "mcpServers": {
    "onecite": {
      "command": "python",
      "args": ["-m", "onecite_mcp.mcp_server"]
    }
  }
}
```

3. **重启MCP desktop client**

4. **测试**
在MCP client中输入：
```
使用OneCite帮我生成这篇论文的引用：10.1038/nature14539
```

### 方法2：在editor client中使用

1. **安装OneCite**
```bash
pip install onecite
```

2. **配置editor client**

在editor client设置中添加MCP服务器配置（`.cursor/settings.json`）：
```json
{
  "mcpServers": {
    "onecite": {
      "command": "python",
      "args": ["-m", "onecite_mcp.mcp_server"]
    }
  }
}
```

3. **重启editor client**

### 方法3：命令行测试

```bash
# 启动MCP服务器
python -m onecite_mcp.mcp_server
```

## 🛠️ 可用工具

### 1. cite - 生成单个引用
```json
{
  "tool": "cite",
  "arguments": {
    "source": "10.1038/nature14539",
    "style": "bibtex"
  }
}
```

**支持的输入格式：**
- DOI: `10.1038/nature14539`
- arXiv ID: `1706.03762`
- 论文标题: `Attention is all you need`
- GitHub URL: `https://github.com/tensorflow/tensorflow`
- Zenodo DOI: `10.5281/zenodo.3233118`

**支持的格式：**
- `bibtex` - BibTeX格式
- `apa` - APA格式
- `mla` - MLA格式

### 2. batch_cite - 批量生成引用
```json
{
  "tool": "batch_cite",
  "arguments": {
    "sources": [
      "10.1038/nature14539",
      "1706.03762",
      "Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning."
    ],
    "style": "apa"
  }
}
```

## 📝 使用示例

### 示例1：生成DOI引用
**输入：**
```
使用cite工具为DOI: 10.1038/nature14539生成BibTeX引用
```

**输出：**
```bibtex
@article{LeCun2015Deep,
  doi = "10.1038/nature14539",
  title = "Deep learning",
  author = "LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey",
  journal = "Nature",
  year = 2015,
  volume = 521,
  number = 7553,
  pages = "436-444"
}
```

### 示例2：批量处理
**输入：**
```
使用batch_cite为以下文献生成APA格式引用：
- 10.1038/nature14539
- Attention is all you need
```

**输出：**
```
LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. Nature, 521(7553), 436-444.

Vaswani, A., Shazeer, N., Parmar, N., ... (2017). Attention Is All You Need. Advances in Neural Information Processing Systems.
```

## 🔍 故障排查

### 问题1：命令未找到
```bash
# 确保onecite已正确安装
pip install --upgrade onecite

# 验证安装
python -c "import onecite_mcp; print('OK')"
```

### 问题2：MCP服务器无法启动
```bash
# 检查Python路径
which python
# 或 Windows:
where python

# 使用完整路径
{
  "command": "/path/to/python",
  "args": ["-m", "onecite_mcp.mcp_server"]
}
```

### 问题3：权限问题
```bash
# 使用用户安装
pip install --user onecite
```

## 📚 更多信息

- **GitHub**: https://github.com/HzaCode/OneCite
- **PyPI**: https://pypi.org/project/onecite/
- **MCP官方文档**: https://modelcontextprotocol.io
- **问题反馈**: https://github.com/HzaCode/OneCite/issues

## 🎯 特性

- ✅ 支持7种以上文献类型（期刊、会议、书籍、软件、数据集等）
- ✅ 智能识别DOI、arXiv、ISBN、GitHub等标识符
- ✅ 多格式输出（BibTeX、APA、MLA）
- ✅ 批量处理
- ✅ 自动补全元数据
- ✅ 支持10+学术数据库

## 📄 许可证

MIT License - 详见项目仓库


