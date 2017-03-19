$(function() {
  $('#standard').uploadifive({
    'uploadScript' : '/upload/',
    'buttonText'   : '选择答案文件',
    'fileObjName' : 'standard',
    'auto' : true,
    'multi' : false,
    'queueSizeLimit' : 2,
    'width' : 200,
    'fileType' : 'application/pdf',
    'formData' : {'token' : $.token},
    'onUploadComplete' : function(file, data) {
        // alert('The file ' + file.name + ' uploaded successfully.');
        $('#uploadifive-standard').remove();
    }
  });

  $('#answers').uploadifive({
    'uploadScript' : '/upload/',
    'buttonText'   : '选择答卷文件（可多选）',
    'fileObjName' : 'answers',
    'auto' : true,
    'multi' : true,
    'width' : 200,
    // 'queueSizeLimit' : 1,
    'fileType' : 'application/pdf',
    'formData' : {'token' : $.token},
    'onUploadComplete' : function(file, data) {
        // alert('The file ' + file.name + ' uploaded successfully.');
        $('#uploadifive-answers').remove();
    }
  });

});
