" general_batch_replace.vim - 通用 Vim 批量搜索替换脚本
" 特性：支持多模式字典、递归搜索、错误抑制、操作日志、类型过滤
" 用法：将本文件放置于目标目录，用 Vim 打开，执行`:so %`
"

" 1. 配置区 - 根据需求修改 -----------------------------------------------{{{1

" target_files -----------------------------------------------------------{{{2
" 几种常见配置方案（根据需要取消注释其中一种）：
"
" 方案 1：搜索所有文件（递归当前目录及所有子目录下的所有文件，包括隐藏文件）
" let g:target_files = '**/*'
"
" 方案 2：搜索特定类型的文本文件（常见源码和文档）
" let g:target_files = '**/*.txt **/*.md **/*.py **/*.js **/*.html **/*.css'
let g:target_files = 'Testing_Guide.md Version_management_guide.md HANDLER_DEVELOPMENT_GUIDE.md new_site_handler_template.py'
"
" 方案 3：仅搜索当前目录下的文件（不递归子目录）
" let g:target_files = '*'
"
" 方案 4：搜索特定目录下的所有文件（例如 'src' 目录下）
" let g:target_files = 'src/**/*'
"
" 方案 5：混合多种模式，并排除特定目录（需要外部工具如 ripgrep 配合，此处仅为示例思路）
" 提示：可结合 systemlist('rg --files --glob "!node_modules"') 等命令生成列表

" ignore_patterns --------------------------------------------------------{{{2
" 要临时忽略的文件模式列表 （用于提升搜索效率）

" 常见忽略模式示例（根据需要取消注释或修改）：
" 排除脚本自身，防止自修改
let s:current_script_name = expand('<sfile>:t')
let g:ignore_patterns = [
    \ s:current_script_name,
    \ ]

" 更多可选的忽略模式（可根据项目类型启用）
let g:ignore_patterns += ['.git']                   " git 相关目录
let g:ignore_patterns += ['.venv', '__pycache__']   " python 相关目录
let g:ignore_patterns += ['*.swp', '*.bak']         " vim 相关文件
let g:ignore_patterns += ['*.jpg', '*.jpeg', '*.gif', '*.png', '*.webp', '*.psd']   " 图片文件
let g:ignore_patterns += ['*.ico', '*.gfie']        " 图标文件
let g:ignore_patterns += ['*.so', '*.dll', '*.exe']  " 其他二进制文件
" let g:ignore_patterns += ['*.log', '*.tmp', '*.cache']  " 日志和临时文件
" let g:ignore_patterns += ['dist', 'build', 'out']  " 其他构建目录

" replacement_dict -------------------------------------------------------{{{2
" 替换字典 【Pattern: 替换内容】
" 核心替换规则：始终启用且稳定的规则
let g:replacement_dict = {
    \ 'MarkURLdown': 'MarkdownAll',
    \ 'markurldown': 'markdownall',
    \ }

" 可选或实验性规则：根据需要快速启用/禁用
" let g:replacement_dict['\<old_function\>']    = 'new_function'
" let g:replacement_dict['\d\{4}-\d\{2}-\d\{2}'] = 'DATE_REPLACED'
" let g:replacement_dict['\s\+$']                = ''  " 删除行尾空格

" 条件规则示例：可以结合 if 语句动态添加
" if some_condition
"     let g:replacement_dict['DebugPattern'] = 'ProductionText'
" endif

" 搜索替换选项 -----------------------------------------------------------{{{2
let g:case_sensitive   = 1              " 1=区分大小写，0=不区分
let g:use_regex        = 1              " 1=使用正则表达式，0=纯文本匹配
let g:confirm_each     = 0              " 1=每次替换前确认，0=直接替换
let g:backup_files     = 0              " 1=创建备份文件，0=不备份

" 2. 准备工作 ------------------------------------------------------------{{{1

" 记录脚本执行前的初始缓冲区编号，用于最终恢复用户环境
let s:original_buffer = bufnr('%')
let s:original_window = winnr()

" 自动将工作目录切换到本脚本所在目录
silent! execute 'cd ' . fnameescape(expand('%:p:h'))

" 初始化脚本内部使用的统计变量
" 这些变量用于记录操作过程中的各种统计信息
let g:total_replacements = 0             " 记录总共执行的替换次数
let g:updated_files      = []            " 记录被修改的文件路径列表
let g:searched_patterns  = 0             " 记录已搜索的模式数量
let g:matched_patterns   = 0             " 记录找到匹配的模式数量

" 输出相关变量
let s:output_lines = []                  " 保存所有输出行
let s:start_time = ''                    " 记录开始时间（显示用）
let s:end_time = ''                      " 记录结束时间（显示用）
let s:start_reltime = []                 " 记录开始时间（计算用）
let s:end_reltime = []                   " 记录结束时间（计算用）

" 3. 函数定义 - 核心逻辑 -------------------------------------------------{{{1

" 输出缓冲区管理函数 -----------------------------------------------------{{{2
" 注意：现在使用延迟创建策略，所有输出先保存到 s:output_lines 数组中

" 输出一行文本（保存到数组）
function! s:OutputLine(text)
    call add(s:output_lines, a:text)
endfunction

" 获取当前时间（毫秒级）的统一函数
function! s:GetCurrentTimeWithMs()
    " 使用单一时间源避免不同步问题
    let l:current_time = localtime()
    let l:reltime_now = reltime()
    let l:reltime_str = reltimestr(l:reltime_now)

    " 从 reltimestr 结果中提取毫秒（格式类似 "12345.678"）
    let l:dot_pos = stridx(l:reltime_str, '.')
    if l:dot_pos >= 0 && len(l:reltime_str) > l:dot_pos + 1
        let l:ms_str = strpart(l:reltime_str, l:dot_pos + 1, 3)
        let l:ms_part = printf("%03d", str2nr(l:ms_str))
    else
        let l:ms_part = "000"
    endif

    " 使用同一秒数确保一致性
    return strftime("%Y-%m-%d %H:%M:%S", l:current_time) . '.' . l:ms_part
endfunction

" 输出带时间戳的消息
function! s:OutputMessage(message)
    " 记录真实的操作时间（毫秒级）- 使用统一的时间获取函数
    let l:current_time = s:GetCurrentTimeWithMs()
    let l:current_reltime = reltime()
    let l:time_parts = split(l:current_time, ' ')
    let l:time_part = l:time_parts[1]  " HH:MM:SS.mmm
    let l:timestamp = "[" . l:time_part . "] "

    " 如果是第一次调用，记录开始时间
    if empty(s:start_time)
        let s:start_time = l:current_time
        let s:start_reltime = l:current_reltime
    endif

    " 每次调用都更新结束时间
    let s:end_time = l:current_time
    let s:end_reltime = l:current_reltime

    call s:OutputLine(l:timestamp . a:message)
endfunction

" 输出分隔线
function! s:OutputSeparator()
    call s:OutputLine(repeat("-", 50))
endfunction

" 计算执行耗时
function! s:CalculateElapsedTime()
    if empty(s:start_reltime) || empty(s:end_reltime)
        return "未知"
    endif

    " 使用 reltime() 计算精确时间差（更可靠）
    let l:elapsed_reltime = reltime(s:start_reltime, s:end_reltime)
    let l:elapsed_str = reltimestr(l:elapsed_reltime)
    
    " 解析 elapsed_str（格式类似 "1.234567"）
    let l:elapsed_float = str2float(l:elapsed_str)
    let l:elapsed_ms = float2nr(l:elapsed_float * 1000)

    " 如果时间差为负（不应该发生），返回错误
    if l:elapsed_ms < 0
        return "时间计算错误（结束时间早于开始时间）"
    endif

    " 格式化输出
    if l:elapsed_ms < 1000
        return l:elapsed_ms . " 毫秒"
    elseif l:elapsed_ms < 60000
        let l:seconds = l:elapsed_ms / 1000
        let l:ms = l:elapsed_ms % 1000
        return l:seconds . "." . printf("%03d", l:ms) . " 秒"
    elseif l:elapsed_ms < 3600000
        let l:minutes = l:elapsed_ms / 60000
        let l:remaining_ms = l:elapsed_ms % 60000
        let l:seconds = l:remaining_ms / 1000
        let l:ms = l:remaining_ms % 1000
        return l:minutes . " 分 " . l:seconds . "." . printf("%03d", l:ms) . " 秒"
    elseif l:elapsed_ms < 86400000
        let l:hours = l:elapsed_ms / 3600000
        let l:remaining_ms = l:elapsed_ms % 3600000
        let l:minutes = l:remaining_ms / 60000
        let l:remaining_ms = l:remaining_ms % 60000
        let l:seconds = l:remaining_ms / 1000
        let l:ms = l:remaining_ms % 1000
        return l:hours . " 小时 " . l:minutes . " 分 " . l:seconds . "." . printf("%03d", l:ms) . " 秒"
    else
        let l:days = l:elapsed_ms / 86400000
        let l:remaining_ms = l:elapsed_ms % 86400000
        let l:hours = l:remaining_ms / 3600000
        let l:remaining_ms = l:remaining_ms % 3600000
        let l:minutes = l:remaining_ms / 60000
        let l:remaining_ms = l:remaining_ms % 60000
        let l:seconds = l:remaining_ms / 1000
        let l:ms = l:remaining_ms % 1000
        return l:days . " 天 " . l:hours . " 小时 " . l:minutes . " 分 " . l:seconds . "." . printf("%03d", l:ms) . " 秒"
    endif
endfunction


" 替换函数：执行实际的搜索替换操作 ---------------------------------------{{{2
function! s:PerformReplacement(pattern, replacement)
    " 构建搜索模式（与 ProcessPattern 中的逻辑保持一致）
    let l:search_pattern = a:pattern
    if !g:case_sensitive
        let l:search_pattern = '\c' . l:search_pattern  " 忽略大小写
    else
        let l:search_pattern = '\C' . l:search_pattern  " 区分大小写
    endif
    if !g:use_regex
        let l:search_pattern = '\V' . l:search_pattern  " 原义匹配(very nomagic)
    endif

    " 构建替换命令
    let l:flags = 'ge'                   " g:全局，e:抑制错误
    if g:confirm_each
        let l:flags = 'gce'              " g:全局，c:确认，e:抑制错误
    endif

    " 执行替换
    execute 'silent! %s/' . l:search_pattern . '/' . a:replacement . '/' . l:flags

    " 记录被修改的文件
    if &modified && index(g:updated_files, expand('%')) == -1
        call add(g:updated_files, expand('%'))
    endif
endfunction

" 在指定缓冲区中执行替换（不切换窗口）
function! s:PerformReplacementInBuffer(bufnr, pattern, replacement)
    " 保存当前状态
    let l:current_buf = bufnr('%')
    let l:current_win = winnr()

    " 构建替换命令
    let l:flags = 'ge'                   " g:全局，e:抑制错误
    if g:confirm_each
        let l:flags = 'gce'              " g:全局，c:确认，e:抑制错误
    endif

    " 临时切换到目标缓冲区进行替换
    if bufexists(a:bufnr)
        " 在新窗口中打开缓冲区
        execute 'silent! split | buffer ' . a:bufnr

        " 执行替换
        execute 'silent! %s/' . a:pattern . '/' . a:replacement . '/' . l:flags

        " 记录被修改的文件
        if &modified
            let l:file_path = expand('%')
            if !empty(l:file_path) && index(g:updated_files, l:file_path) == -1
                call add(g:updated_files, l:file_path)
            endif
        endif

        " 关闭临时窗口
        close

        " 返回到原始窗口
        execute l:current_win . 'wincmd w'
    endif
endfunction

" 主处理函数：处理单个搜索模式 -------------------------------------------{{{2
function! s:ProcessPattern(pattern, replacement)
    let g:searched_patterns += 1

    " 构建搜索模式 （处理大小写和正则选项）
    let l:search_pattern = a:pattern
    if !g:case_sensitive
        let l:search_pattern = '\c' . l:search_pattern  " 忽略大小写
    else
        let l:search_pattern = '\C' . l:search_pattern  " 区分大小写
    endif
    if !g:use_regex
        let l:search_pattern = '\V' . l:search_pattern  " 原义匹配(very nomagic)
    endif

    " 清空 quickfix 列表，确保每次搜索都是干净的
    call setqflist([])

    " 使用 vimgrep 搜索模式
    silent! execute 'vimgrep /' . l:search_pattern . '/gj ' . g:target_files

    " 检查是否有匹配
    let l:initial_matches = len(getqflist())
    if l:initial_matches > 0
        let g:matched_patterns += 1
        call s:OutputLine("  - 找到: " . l:initial_matches . " 个匹配项")

        " 🔧 新增：过滤掉需要忽略的文件匹配项
        let l:filtered_list = []
        let l:ignored_count = 0

        for l:item in getqflist()
            let l:should_ignore = 0

            " 获取匹配项对应的文件名
            let l:file_path = ''
            if has_key(l:item, 'filename') && !empty(l:item.filename)
                let l:file_path = l:item.filename
            elseif l:item.bufnr > 0
                let l:file_path = bufname(l:item.bufnr)
            endif

            " 检查当前匹配项的文件名是否匹配忽略列表中的任何模式
            if !empty(l:file_path)
                " 提取文件名（不包含路径）进行匹配
                let l:filename_only = fnamemodify(l:file_path, ':t')

                for l:ignore_pattern in g:ignore_patterns
                    " 如果文件名匹配模式，match() 返回匹配开始的索引（>=0）；不匹配则返回 -1
                    if match(l:filename_only, l:ignore_pattern) >= 0 || match(l:file_path, l:ignore_pattern) >= 0
                        let l:should_ignore = 1
                        let l:ignored_count += 1
                        break
                    endif
                endfor
            endif

            " 只有当文件不在忽略列表中时，才加入最终处理列表
            if !l:should_ignore
                call add(l:filtered_list, l:item)
            endif
        endfor

        " 显示过滤信息
        if l:ignored_count > 0
            call s:OutputLine("  - 忽略: " . l:ignored_count . " 个匹配项（在忽略列表中）")
        endif

        " 如果过滤后还有匹配项，则执行替换
        if len(l:filtered_list) > 0
            call setqflist(l:filtered_list)
            let g:total_replacements += len(l:filtered_list)

            " 统计涉及的文件数量
            let l:file_count = {}
            for l:item in l:filtered_list
                let l:file_path = bufname(l:item.bufnr)
                if !empty(l:file_path)
                    let l:file_count[l:file_path] = 1
                endif
            endfor
            let l:unique_files = len(keys(l:file_count))

            call s:OutputLine("  - 执行替换: " . len(l:filtered_list) . " 个匹配项，涉及 " . l:unique_files . " 个文件")

            " 使用 cfdo 执行替换（简单直接）
            silent! cfdo call s:PerformReplacement(a:pattern, a:replacement)
        else
            call s:OutputLine("  - 跳过: 所有匹配项都在忽略列表中")
        endif

        " 清空 quickfix 列表以备下次使用
        call setqflist([])
    else
        call s:OutputLine("  - 未找到匹配项")
    endif
endfunction

" 保存函数：确保所有被修改的文件都被保存到磁盘 ---------------------------{{{2
function! s:SaveAllModifiedFiles()
    let l:saved_count = 0
    " 保存当前窗口状态
    let l:current_window = winnr()
    let l:current_buffer = bufnr('%')

    " 遍历所有被记录为已修改的文件
    for l:file_path in g:updated_files
        " 通过文件名找到缓冲区编号
        let l:target_bufnr = bufnr(l:file_path)

        if l:target_bufnr != -1  " 确保缓冲区存在
            " 切换到目标缓冲区
            execute 'buffer' l:target_bufnr

            " 对确实被修改的缓冲区，执行保存操作
            if &modified
                silent! write
                let l:saved_count += 1
                call s:OutputLine("  ✓ 已保存: " . l:file_path)
            endif
        endif
    endfor

    " 恢复到原始窗口
    if winnr('$') >= l:current_window
        execute l:current_window . 'wincmd w'
    endif
    if bufnr('%') != l:current_buffer && bufwinnr(l:current_buffer) != -1
        execute bufwinnr(l:current_buffer) . 'wincmd w'
    endif

    if l:saved_count > 0
        call s:OutputMessage("成功保存 " . l:saved_count . " 个文件")
    endif
endfunction

" 4. 脚本主体执行逻辑 ----------------------------------------------------{{{1
" 保存原始设置以便后续恢复
let s:original_ei = &eventignore
let s:original_hidden = &hidden
let s:original_backup = &backup

try
    " 配置执行环境
    set eventignore=all      " 忽略所有自动事件以防干扰
    set hidden               " 允许缓冲区隐藏
    if g:backup_files        " 是否启用备份
        set backup
    else
        set nobackup
    endif

    " 记录开始时间（不输出消息）- 毫秒级
    let s:start_time = s:GetCurrentTimeWithMs()
    let s:start_reltime = reltime()

    " 初始化 Markdown 格式输出
    call s:OutputLine("# 批量搜索替换操作日志")
    call s:OutputLine("")
    call s:OutputLine("> 提示: 按 `q` 或 `Esc` 关闭窗口")
    call s:OutputLine("> 说明: 关闭时将自动删除，不会保存到磁盘。")
    call s:OutputLine("")
    call s:OutputLine("## 执行信息")
    call s:OutputLine("")
    call s:OutputLine("- 工作目录: `" . getcwd() . "`")
    call s:OutputLine("- 搜索文件: `" . g:target_files . "`")
    call s:OutputLine("- 模式数量: " . len(items(g:replacement_dict)))
    call s:OutputLine("")
    call s:OutputLine("## 执行过程")
    call s:OutputLine("")

    " 循环处理替换字典中的每个模式
    for [pattern, replacement] in items(g:replacement_dict)
        call s:OutputMessage("处理模式: `" . pattern . "` → `" . replacement . "`")
        call s:ProcessPattern(pattern, replacement)
    endfor

    " 确保所有被修改的文件都被保存
    if len(g:updated_files) > 0
        call s:OutputLine("")
        call s:OutputLine("## 被修改的文件")
        call s:OutputLine("")
        call s:OutputMessage("正在保存所有被修改的文件...")
        call s:SaveAllModifiedFiles()
    endif

    " 成功完成提示
    call s:OutputLine("")
    call s:OutputMessage("批量替换操作执行完成！")

finally
    " 恢复 vim 原始设置
    let &eventignore = s:original_ei
    let &hidden = s:original_hidden
    let &backup = s:original_backup

    " 确保回到原始脚本缓冲区
    if bufexists(s:original_buffer)
        execute 'buffer ' . s:original_buffer
    endif

    " 创建垂直分割的 Scratch 缓冲区（左侧）
    vnew

    " 设置 Scratch 缓冲区属性
    setlocal buftype=nofile
    setlocal bufhidden=wipe
    setlocal noswapfile
    setlocal nobuflisted
    setlocal nowrap
    setlocal number

    " 设置缓冲区名称和文件类型
    silent! file [Scratch:\ BatchReplace\ Output.md]
    setlocal filetype=markdown

    " 添加键盘映射
    nnoremap <buffer><silent> q :close<CR>
    nnoremap <buffer><silent> <Esc> :close<CR>

    " 添加简洁的最终统计报告
    call add(s:output_lines, '')
    call add(s:output_lines, '## 统计信息')
    call add(s:output_lines, '')
    call add(s:output_lines, '- 搜索模式数: ' . g:searched_patterns)
    call add(s:output_lines, '- 匹配模式数: ' . g:matched_patterns)
    call add(s:output_lines, '- 总替换次数: ' . g:total_replacements)
    call add(s:output_lines, '- 修改文件数: ' . len(g:updated_files))
    call add(s:output_lines, '')
    call add(s:output_lines, '- 开始时间: ' . s:start_time)
    call add(s:output_lines, '- 完成时间: ' . s:end_time)
    call add(s:output_lines, '- 总耗时: ' . s:CalculateElapsedTime())

    " 将所有保存的输出行写入缓冲区
    for line in s:output_lines
        put =line
    endfor

    " 删除第一行空行
    1delete
endtry

" Created:  2025/10/02 12:51:18
" Modified: 2025/10/03 01:55:00
