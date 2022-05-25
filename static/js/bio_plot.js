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

// 检查任务状态
function checkJob(url, data){
    let rslt = "";
    $.ajax({
        url: url
        ,type: "post"
        ,data: data
        ,async: false
        ,success: function (data) {
            rslt = data;
        }
        ,error: function (jqXHR, textStatus, errorThrown){
            rslt = {code: "done"}
        }
    });
    return rslt
}

// 定时监控任务的状态，刷新任务状态表格，直到任务终止
function monitorJob(url, data, interval, table_func, table_id){
    let status = checkJob(url, data);
    console.log(status);
    while (status["code"] === "run"){
        setTimeout(function(){},interval);
        table_func.reload(table_id, {data: status});
        status = checkJob(url, data);
    }
    return status

}