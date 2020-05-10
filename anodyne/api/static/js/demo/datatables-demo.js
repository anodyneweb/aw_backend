// Call the dataTables jQuery plugin
$(document).ready( function() {
$('#dataTable').DataTable( {
		"lengthMenu": [[20, 100, 200, -1], [20, 100, 200, "All"]]
    } );
} );
