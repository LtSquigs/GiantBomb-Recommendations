var POST_URL = "/";
	
loading_text = ["Asking the Dark Brotherhood for advice...",
				"Tabulating the game scores...",
				"Calling up Will Wright for advice...",
				"TANGO DOWN IN SECTOR ONE ALPHA...",
				"Fribulating the covectoring correlation quotient...",
				"Figuring it all out...",
				"Loading..."]

$(document).ready( function() {
	$('#reccsBox').hide();
	$('#errBox').hide();
	$('#loading').hide();

	centerObject($('#nameBox'));
	centerObject($('#reccsBox'));
	centerObject($('#errBox'));
	centerObject($('#loading'));
	
	
	$(window).resize( function(e) {
		centerObject($('#nameBox'));
		centerObject($('#reccsBox'));
		centerObject($('#errBox'));
		centerObject($('#loading'));
	});
	
	$('#submitName').click(function (e) {
		getReccs();
	});
	
	$('#userName').keypress(function(e) {
		if(e.keyCode == 13)
		{
			getReccs();
		}
	});
	
	$('.backLink').click(function (e) {
		returnToStart();
	});
});

var loadingTimeout = null;

function startLoadingCycle() {
	cycleLoadingText();
	$('#loading').show();
	loadingTimeout = setTimeout("cycleLoadingText()", 5000);
}

function cycleLoadingText() {

	var text = Math.floor(Math.random() * loading_text.length);
	
	$('#loadingText').text(loading_text[text])
	
	centerObject($('#loading'));
	loadingTimeout = setTimeout("cycleLoadingText()", 5000);
}

function stopLoadingCycle() {
	if(loadingTimeout != null)
	{	
		$('#loading').hide();
		clearTimeout(loadingTimeout);
		loadingTimeout = null;
	}
}

function returnToStart() {

	$('.reccsRow').remove();
	$('#userName').val("");

	$('#errBox').hide();
	$('#loading').hide();
	$('#reccsBox').hide();
	$('#nameBox').show();
	$('#updateBox').show();
}

function getReccs() {
	$('#nameBox').hide();
	startLoadingCycle();
	$.ajax({
		url: POST_URL,
		type: "POST",
		dataType: "json",
		data: {
			userName: $('#userName').val(),
		},
		success: function (data) {
			stopLoadingCycle();
			if(data['error'] == 'true' || data['error'] == true)
			{
				$('#errorText').text(data['errtext']);
				$('#updateBox').hide();
				$('#nameBox').hide();
				$('#errBox').show();
				return;
			}
			
			//$('#reccsBox').prepend("<h1>Your Reccomendations:</h1>");
			
			var rowSize = 3;
			var curtr = null;
			
			for(var i = 0; i < data['reccomends'].length; i++)
			{
				if(i % rowSize == 0) {
					curtr = $('<tr class="reccsRow"></tr>').appendTo($('#reccs'));
				}
				var reccs = data['reccomends'][i];
				image = reccs.image;
				name = reccs.name;
				
				var image = $("<img></img>").attr('src', image);
				var nameSpan = $("<span></span>").text(name);
				
				var td = $('<td></td>').append(image).append(nameSpan);
				
				$(curtr).append(td);
				
			}
			
			$('#updateBox').hide();
			$('#nameBox').hide();
			$('#reccsBox').show();
		},
		
		error: function(d, e, f) {
			stopLoadingCycle();
			$('#errorText').text("An unkown error has occured, sorry.");
			$('#updateBox').hide();
			$('#nameBox').hide();
			$('#errBox').show();
		}
	});
}



function centerObject(obj)
{
	$(obj).css({
		position:'absolute',
		left: ($(window).width() - $(obj).outerWidth())/2,
		top: ($(window).height() - $(obj).outerHeight())/2
	});
}