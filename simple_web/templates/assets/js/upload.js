function enable_if_true(element, condition) {
  if(condition)
    element.prop('disabled', false);
}


$(function() {

  $.uploaded_standard = false;
  $.uploaded_answers = false;

  

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
        $.uploaded_standard = true;
        enable_if_true($('#submit'), $.uploaded_standard && $.uploaded_answers);
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
        $.uploaded_answers = true;
        enable_if_true($('#submit'), $.uploaded_standard && $.uploaded_answers);
    }
  });

});
