# 实验 11-1 · 在沙盒中编辑表格，再受控另存

先用 Bubblewrap 从空目录搭一个最小沙盒，再跑完整实验比较两种后端。示例使用临时生成的表格。工作进程读取获准的输入，写出带合计列的候选文件。完整实验还会在宿主验证候选内容和保存授权。

## 从空目录搭建 Bubblewrap 沙盒

在允许普通用户创建所需命名空间的 Linux 上，用 Bash 运行下面的示例。需要已安装 Bubblewrap 和 `/usr/bin/python3`。外层 Bash 准备合成文件，最后也由它读回结果。示例直接在沙盒内启动 Python。任务如果要用 Shell 的管道或重定向，就把 Shell 作为沙盒内的启动命令，让它和启动的程序一起受限。

```bash
(
  set -eu
  task_dir=$(mktemp -d)
  trap 'rm -rf -- "$task_dir"' EXIT
  mkdir "$task_dir/output"
  printf 'Month,Travel,Meals\nJan,12,8\n' > "$task_dir/expenses.csv"
  printf 'A second test file\n' > "$task_dir/neighbor.csv"

  runtime=()
  for path in /usr /lib /lib64; do
    if [ -d "$path" ]; then
      runtime+=(--ro-bind "$path" "$path")
    fi
  done
  launcher=()
  "${launcher[@]}" bwrap --unshare-all --die-with-parent --new-session --clearenv \
    "${runtime[@]}" \
    --ro-bind "$task_dir/expenses.csv" /input/expenses.csv \
    --bind "$task_dir/output" /output --chdir /output \
    -- /usr/bin/python3 -I -B -c '
import csv
from pathlib import Path

with Path("/input/expenses.csv").open(newline="") as stream:
    row = next(csv.DictReader(stream))
month = row["Month"]
total = int(row["Travel"]) + int(row["Meals"])
Path("candidate.csv").write_text(f"Month,Total\n{month},{total}\n")
assert not Path("/input/neighbor.csv").exists()
'
  cat "$task_dir/output/candidate.csv"
)
```

预期输出是 `Month,Total` 和 `Jan,20`。从上往下看挂载清单。运行时目录只读，输入只映射了 `expenses.csv`，输出则连着宿主的临时目录。独立的网络命名空间用于本地计算，解释器在清理过的环境中启动。脚本检查相邻文件在这个视图中不可见，宿主仍能从输出目录读回候选结果。可以把输出目录的 `--bind` 改为 `--ro-bind` 再跑一次，观察 Python 怎样在写候选文件时退出。然后恢复可写挂载。

### 给任务加资源限额

如果 Linux 使用 cgroup v2，且 systemd 用户会话可以使用相应的控制器，把示例中的 `launcher=()` 改成下面一行，再跑一遍。

```bash
launcher=(systemd-run --user --scope --quiet -p CPUQuota=50% -p MemoryMax=128M -p TasksMax=16 -p RuntimeMaxSec=10s)
```

这样只把 `bwrap` 及其子进程放进受限的任务组。外层 Bash 继续负责清理和取回结果。任务组达到运行时限时，systemd 会开始停止组内进程。这些数值只是小样例的预算，应用还要单独配置工作区空间，并在目标机器确认各项限额实际生效。参数对应的控制项见 [systemd 资源控制](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)和[任务组说明](https://www.freedesktop.org/software/systemd/man/latest/systemd.scope.html)。

## 运行完整的对照实验

完整实验还需要支持硬链接的临时文件系统。`landlock` 后端需要 C 编译器、包含网络规则定义的 Linux UAPI 头文件和内核 Landlock ABI 4 或更高版本。在普通用户身份下运行。若发行版安全策略阻止 Bubblewrap 启动，可以在已允许该方式的 Linux 环境里重试，或先运行 Landlock 后端。

在仓库根目录运行下列命令。

```bash
python3 chapter11/local-spreadsheet-sandbox/main.py --backend bwrap
python3 chapter11/local-spreadsheet-sandbox/main.py --backend landlock
```

脚本使用 Python 标准库。所有文件和本机 TCP 监听都由脚本创建，任务结束后回收。它无需模型 API、个人文档或外部网络。后端启动失败时直接退出。

## 验收

两种后端都会输出十个检查字段。全部为 `true` 时退出码为零。

- 助手能读取输入，在工作区生成正确的合计列。相邻表格读不到，获准输入不能被截断，不能连接宿主预先启动并确认可达的本机 TCP 端口。
- 宿主核对输入副本与原件都未被执行进程改动，再读取并验证候选文件，另存到获准路径。宿主拒绝覆盖原件，同名目的文件保留原样。模拟原件在任务中变化后，停止本次提交，保留用户的新版本。

### 把同一组权限写成 Landlock 规则

可以对照三个文件读。宿主在 `main.py` 准备输入副本、启动任务、验收并另存。`worker.py` 里的计算和访问检查供两个后端共用。在 `landlock.c` 中，从 `handled_access_fs` 和 `handled_access_net` 看起，找出规则集接管了哪些文件与 TCP 操作。接着看三次针对任务文件的 `allow_path` 调用。输入副本和脚本只读，输出目录允许创建和写入文件，相邻文件没有获准读取。启动器先让内核应用规则，再执行 Python。宿主仍能读取原件、监听测试端口和提交输出。

想看规则怎样影响结果，可以在实验的副本里把 `allow_path(ruleset, argv[3], read | write)` 改成只给 `read`。再次运行 Landlock 后端时，脚本应在创建候选文件那一步被内核拒绝。恢复原规则后，再通过正常编辑和拒绝越权的检查。移到自己的任务时，可以用同样的方法逐项调整和验收。实验中的 Landlock 网络规则覆盖 TCP 绑定及连接。接入模型生成的命令前，还需验收实际使用的凭证、继承句柄、其他网络与 IPC、资源限额和进程回收。
