function initializeJobTable(table, id) {
    // 任务状态表格初始化
    table.render({
            elem: '#' + id
            ,height: 80
            ,size: 'sm'
            ,cols: [[
                {field: 'jobid', title: '任务ID', align:'center'}
                ,{field: 'stat', title: '任务状态', align:'center', toolbar: '#toolbar-tools'}
                ,{field: 'flag', title: '任务标签', align:'center'}
                ,{field: 'time', title: 'time', align:'center'}
                ,{field: 'error', title: '报错日志', align:'center'}
                ]]
            ,data: [{"jobid": "", "stat": "", "flag": "", "time": "", "msg": ""}]
        });
}