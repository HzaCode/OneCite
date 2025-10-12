# OneCite MCP Server Deployment Guide

OneCite MCP Server is a powerful academic citation management tool that integrates with MCP clients through the Model Context Protocol (MCP).

## ✨ Features

- **Multi-source Support**: DOI, arXiv ID, paper titles, URLs
- **Multi-format Output**: BibTeX, APA, MLA
- **Batch Processing**: Process multiple citations at once
- **Smart Recognition**: Automatic literature type and metadata identification
- **Real-time Validation**: DOI verification through CrossRef and other databases

## 📦 Installation

```bash
pip install onecite
```

## 🚀 Usage

### MCP desktop client Integration

1. **Install OneCite**
```bash
pip install onecite
```

2. **Configure MCP desktop client**

Edit MCP desktop client configuration file:
- **macOS**: `~/Library/Application Support/MCP client/claude_desktop_config.json`
- **Windows**: `%APPDATA%\MCP client\claude_desktop_config.json`

Add the following configuration:
```json
{
  "mcpServers": {
    "onecite": {
      "command": "onecite-mcp"
    }
  }
}
```

3. **Restart MCP desktop client**

4. **Test**
Input in MCP client:
```
Generate a citation for this paper: 10.1038/nature12373
```

**Expected Result**:
```bibtex
@article{Kucsko2013Nanometrescale,
  doi = "10.1038/nature12373",
  title = "Nanometre-scale thermometry in a living cell",
  author = "Kucsko, G. and Maurer, P. C. and Yao, N. Y. and Kubo, M. and Noh, H. J. and Lo, P. K. and Park, H. and Lukin, M. D.",
  journal = "Nature",
  year = 2013,
  volume = 500,
  number = 7460,
  pages = "54-58",
  publisher = "Springer Science and Business Media LLC",
  url = "https://doi.org/10.1038/nature12373",
  type = "journal-article",
}
```

### editor client Integration

1. **Install OneCite**
```bash
pip install onecite
```

2. **Configure editor client**

Add MCP server configuration to `.cursor/settings.json`:
```json
{
  "mcpServers": {
    "onecite": {
      "command": "onecite-mcp"
    }
  }
}
```

3. **Restart editor client**

## 🛠️ Available Tools

### 1. `cite` - Single Citation Generation

**Function**: Generate citation for a single literature source

**Parameters**:
- `source` (required): Literature source, supports:
  - DOI: `10.1038/nature12373`
  - arXiv ID: `arXiv:1706.03762` or `1706.03762`
  - Paper title: `Attention Is All You Need`
  - URL: `https://arxiv.org/abs/1706.03762`
- `style` (optional): Output format, default `bibtex`
  - `bibtex`: BibTeX format
  - `apa`: APA format
  - `mla`: MLA format

**Example**:
```json
{
  "source": "10.1038/nature12373",
  "style": "bibtex"
}
```

### 2. `batch_cite` - Batch Citation Generation

**Function**: Generate citations for multiple literature sources

**Parameters**:
- `sources` (required): Array of literature sources
- `style` (optional): Output format, default `bibtex`

**Example**:
```json
{
  "sources": [
    "10.1038/nature12373",
    "arXiv:1706.03762",
    "Attention Is All You Need"
  ],
  "style": "apa"
}
```

## 📝 Usage Examples

### Example 1: DOI Citation
**Input**:
```
Generate a BibTeX citation for DOI: 10.1038/nature12373
```

**Output**:
```bibtex
@article{Kucsko2013Nanometrescale,
  doi = "10.1038/nature12373",
  title = "Nanometre-scale thermometry in a living cell",
  author = "Kucsko, G. and Maurer, P. C. and Yao, N. Y. and Kubo, M. and Noh, H. J. and Lo, P. K. and Park, H. and Lukin, M. D.",
  journal = "Nature",
  year = 2013,
  volume = 500,
  number = 7460,
  pages = "54-58",
  publisher = "Springer Science and Business Media LLC",
  url = "https://doi.org/10.1038/nature12373",
  type = "journal-article",
}
```

### Example 2: Batch Processing
**Input**:
```
Generate APA format citations for:
- 10.1038/nature12373
- Attention is all you need
```

**Output**:
```
Kucsko, G., Maurer, P. C., Yao, N. Y., Kubo, M., Noh, H. J., Lo, P. K., Park, H., Lukin, M. D. (2013). Nanometre-scale thermometry in a living cell. *Nature*, 500(7460), 54-58.

Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, L., Polosukhin, I. (2017). Attention Is All You Need. *arXiv preprint*.
```

## ✅ Test Verification

MCP server has been tested with:

- ✅ **DOI Processing**: Nature article (10.1038/nature12373)
- ✅ **arXiv Processing**: Transformer paper (arXiv:1706.03762)
- ✅ **BibTeX Format**: Complete metadata output
- ✅ **APA Format**: Standard academic citation format
- ✅ **Batch Processing**: Multiple sources simultaneously
- ✅ **Error Handling**: Invalid input processing

## 🔍 Troubleshooting

### Issue 1: Command Not Found
```bash
# Ensure onecite is properly installed
pip install --upgrade onecite

# Verify installation
python -c "import onecite_mcp; print('OK')"
```

### Issue 2: MCP Server Won't Start
```bash
# Check Python path
which python
# or Windows:
where python

# Use full path in configuration
{
  "command": "/path/to/python",
  "args": ["-m", "onecite_mcp.mcp_server"]
}
```

### Issue 3: Permission Issues
```bash
# Use user installation
pip install --user onecite
```

## 📚 Additional Information

- **GitHub**: https://github.com/HzaCode/OneCite
- **PyPI**: https://pypi.org/project/onecite/
- **MCP Documentation**: https://modelcontextprotocol.io
- **Issue Reporting**: https://github.com/HzaCode/OneCite/issues

## 🎯 Capabilities

- ✅ Supports 7+ literature types (journal, conference, book, software, dataset, etc.)
- ✅ Smart recognition of DOI, arXiv, ISBN, GitHub identifiers
- ✅ Multi-format output (BibTeX, APA, MLA)
- ✅ Batch processing capabilities
- ✅ Automatic metadata completion
- ✅ Integration with 10+ academic databases

## 📄 License

MIT License - See project repository for details