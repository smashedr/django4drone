$(document).ready(function() {

    $('.form-control').focus(function() {
        $(this).removeClass('is-invalid');
    });

    $('#contact-form').on('submit', function(event){
        event.preventDefault();
        if ($('#submit-btn').hasClass('disabled')) { return; }
        var formData = new FormData($(this)[0]);
        $.ajax({
            url: window.location.pathname,
            type: 'POST',
            data: formData,
            beforeSend: function( jqXHR ){
                $('.contact-processing').show();
                $('#submit-btn').addClass('disabled');
            },
            complete: function(){
                $('.contact-processing').hide();
                $('#submit-btn').removeClass('disabled');
            },
            success: function(data, textStatus, jqXHR){
                console.log('Status: '+jqXHR.status+', Data: '+JSON.stringify(data));
                $('#contact-form').hide();
                $('#submit-success').show();
            },
            error: function(data, textStatus) {
                console.log('Status: '+data.status+', Response: '+data.responseText);
                try {
                    console.log(data.responseJSON);
                    if (data.responseJSON.hasOwnProperty('error_message')) {
                        alert(data.responseJSON['error_message'])
                    } else {
                        $($('#contact-form').prop('elements')).each(function () {
                            if (data.responseJSON.hasOwnProperty(this.name)) {
                                $('#' + this.name + '-invalid').empty().append(data.responseJSON[this.name]);
                                $(this).addClass('is-invalid');
                            }
                        });
                    }
                }
                catch(error){
                    console.log(error);
                    alert('Fatal Error: ' + error)
                }
            },
            cache: false,
            contentType: false,
            processData: false
        });
        return false;
    });

} );
