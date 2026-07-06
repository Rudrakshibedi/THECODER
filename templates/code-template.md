---
name: code-template
version: 1.0.0
description: Reusable output structure for generated source code documents
used_by:
  - coder
---

## Structure
```
# Source Code: <product name>

## Project Structure
A brief ASCII tree showing the files generated in this document.

## Dependencies & Configuration

### <config-file-path>
```<language>
<complete file content>
```

## Source Files

### <relative/path/to/file.ext>
```<language>
<complete file content>
```

### <relative/path/to/next-file.ext>
```<language>
<complete file content>
```

(one section per file — no omissions, no placeholders)
```
