"""Draw the local execution boundary and compare the two Linux mechanisms."""

from introduction import Figure


def execution_boundary():
    figure = Figure(
        '一次本地表格编辑的执行边界',
        'Agent 请求运行命令。宿主执行器依据授权设置沙盒，Shell、Python 和子进程在限制内运行。'
        '操作系统限制文件、网络和计算资源。宿主取回候选文件，核对后按用户授权另存。',
        800,
    )
    figure.box(220, 20, 460, 62)
    figure.text(450, 61, 'Agent 生成 Shell 命令', 28, True)
    figure.path([(450, 82), (450, 118)], arrow=True)
    figure.box(175, 118, 550, 100)
    figure.text(450, 158, '宿主执行器', 28, True)
    figure.text(450, 194, '核对任务授权，启动前设置限制', 26)
    figure.path([(450, 218), (450, 335)], arrow=True)

    figure.parts.append(
        '<rect x="20" y="258" width="860" height="390" rx="12" fill="none" '
        'stroke="#444444" stroke-width="2" stroke-dasharray="9 6"/>'
    )
    figure.text(151, 306, '沙盒边界', 28, True)
    figure.box(175, 335, 550, 62, fill='#dedede')
    figure.text(450, 376, 'Shell 启动 Python，限制传给子进程', 28, True)
    figure.path([(450, 397), (450, 410)])
    figure.text(450, 439, '操作系统约束对宿主资源的访问和用量', 26)
    figure.path([(450, 446), (450, 470)], arrow=True)
    figure.path([(450, 454), (176, 454), (176, 470)], arrow=True)
    figure.path([(450, 454), (724, 454), (724, 470)], arrow=True)
    for x, title, limits in [
        (48, '文件系统', ('输入副本只读', '任务工作区可写')),
        (322, '网络', ('隔离网络或', '按规则限制连接')),
        (596, '计算资源', ('限制 CPU、内存', '和进程数')),
    ]:
        figure.box(x, 470, 256, 139, fill='#ffffff')
        figure.text(x + 128, 508, title, 28, True)
        for index, line in enumerate(limits):
            figure.text(x + 128, 552 + index * 33, line, 26)

    figure.path([(176, 609), (176, 700)], arrow=True)
    figure.text(281, 685, '候选文件', 26)
    figure.box(48, 700, 804, 76)
    figure.text(450, 747, '宿主核对候选文件，按用户授权另存', 28, True)
    figure.save('fig11-1.svg')


def linux_file_access():
    figure = Figure(
        'Bubblewrap 与 Landlock 怎样拦下相邻报表的读取',
        '同一个脚本尝试打开相邻报表。Bubblewrap 的挂载视图没有接入这份文件。'
        'Landlock 保留路径，由内核根据读权限拒绝打开请求。',
        548,
    )
    figure.box(175, 20, 550, 70, fill='#dedede')
    figure.text(450, 65, 'Python 尝试打开相邻报表', 28, True)
    figure.path([(450, 90), (450, 122), (230, 122), (230, 150)], arrow=True)
    figure.path([(450, 122), (670, 122), (670, 150)], arrow=True)
    for x, title, layer, state, result in [
        (30, 'Bubblewrap', '独立的挂载视图', '相邻报表未映射进去', '在这棵目录树上找不到文件'),
        (470, 'Landlock', '内核中的访问规则', '相邻报表未授予读权限', '内核拒绝打开请求'),
    ]:
        center = x + 200
        figure.box(x, 150, 400, 110)
        figure.text(center, 193, title, 29, True)
        figure.text(center, 233, layer, 26)
        figure.path([(center, 260), (center, 308)], arrow=True)
        figure.box(x, 308, 400, 80, fill='#ffffff')
        figure.text(center, 358, state, 27)
        figure.path([(center, 388), (center, 440)], arrow=True)
        figure.box(x, 440, 400, 80)
        figure.text(center, 490, result, 28, True)
    figure.save('fig11-2.svg')


if __name__ == '__main__':
    execution_boundary()
    linux_file_access()
