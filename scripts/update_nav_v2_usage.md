# `update_nav_v2.py` 使用说明

## 1. 工具作用

`scripts/update_nav_v2.py` 用于维护 v2 导航文件 `pie-podcast-nav-v2.md`，并根据 `urls.txt` 与 `pie-srt/v2` 的字幕文件状态执行更新与校验。

支持能力：
- 更新或新增导航条目（按期号倒序）
- 规范化标题跨行问题
- 修复“期号与字幕链接不一致”的明显错链
- 校验导航一致性（重复、错链、缺失字幕文件等）

## 2. 基本命令

在仓库根目录执行：

```bash
python3 scripts/update_nav_v2.py [选项]
```

可用选项：

```bash
--check      # 只校验，不写文件
--dry-run    # 预览更新结果，不写文件
--fix-wrap   # 修复标题跨行（下一行以 ]( 开头）
--fix-links  # 修复字幕链接：第N期 -> pie-epN.mp3.srt
```

默认无选项时执行“更新模式”（会写入导航文件，且可能重命名字幕文件）。

## 3. 输入文件约定

### `urls.txt`

每行包含：
- 一个 URL
- 一个期号（可以是 `190`，也可以包含在 `pie-ep190.mp3` 里）

示例：

```txt
201 https://cdn2.wavpub.com/.../pie-ep201.mp3
https://cdn2.wavpub.com/.../pie-ep200.mp3
```

注意：
- 空行和 `#` 注释行会被忽略
- 同一期号如果给出不同 URL，会报错

### `pie-srt/v2` 目录

若存在如下命名的字幕：

```txt
第201期 AI时代的开源_原文.srt
```

更新模式会尝试重命名为：

```txt
pie-ep201.mp3.srt
```

并把标题 `AI时代的开源` 写入导航。

## 4. 推荐流程（每次更新）

```bash
# 1) 修复历史格式问题（一次或按需）
python3 scripts/update_nav_v2.py --fix-wrap

# 2) 修复明显错链（按需）
python3 scripts/update_nav_v2.py --fix-links

# 3) 先做一致性检查
python3 scripts/update_nav_v2.py --check

# 4) 预览本次更新
python3 scripts/update_nav_v2.py --dry-run

# 5) 确认后正式更新
python3 scripts/update_nav_v2.py

# 6) 再检查一次
python3 scripts/update_nav_v2.py --check
```

## 5. 各模式输出说明

- 更新模式 / `--dry-run`
  - `renamed`: 本次识别并重命名的期号
  - `added`: 本次新插入的期号
  - `updated`: 本次覆盖更新的期号

- `--check`
  - `check passed`: 通过
  - `check failed`: 失败，并列出问题行号与原因

- `--fix-wrap` / `--fix-links`
  - `fixed: N`: 修复条数
  - `fixed: -`: 无需修复

## 6. 常见问题

1. `--check` 报 “multi-line title (not allowed)`  
说明导航里有跨行标题。先跑：

```bash
python3 scripts/update_nav_v2.py --fix-wrap
```

2. `--check` 报 “subtitle linked under epX`  
说明字幕链接期号错位。先跑：

```bash
python3 scripts/update_nav_v2.py --fix-links
```

3. `--check` 报 “subtitle file not found`  
说明导航引用了不存在的字幕文件。需要补齐文件或修正对应链接。

