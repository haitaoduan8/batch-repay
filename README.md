# 批量还款划扣工具

基于 Flet 的批量还款划扣桌面工具，支持试算、划扣、查询功能。

## 功能

- **试算**: 预览还款金额，不实际扣款
- **划扣**: 批量发起还款请求（合并还/按期还）
- **查询**: 查询今日划扣结果
- **Token 持久化**: 自动保存 Token

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

```bash
python batch_repay_app.py
```

## 使用方法

1. 输入 Token（从浏览器 F12 Console 获取: `localStorage.getItem('token')`）
2. 添加借据：
   - 手动输入：`借据编号=产品ID`，每行一条
   - 或导入 CSV 文件（格式：`借据编号,产品ID`）
3. 选择还款类型（合并还/按期还）
4. 点击对应按钮操作

### 产品ID

- `11` = 哈银
- `1` = 廊坊

## 打包成 EXE

```bash
flet build windows
```

生成的 EXE 在 `build/windows/` 目录下。
