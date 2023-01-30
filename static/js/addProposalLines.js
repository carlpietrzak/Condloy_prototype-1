$(document).ready(function () {

    $("#addRow").on("click", function () {
   
	table = $('#myTable')[0];    
        lastRow = table.rows[table.rows.length-3]
        lastRowId = lastRow.id[lastRow.id.length - 1]

        nextRowId = parseInt(lastRowId) + 1

        var newRow = $('<tr class="d-flex" id="row'+nextRowId+'">');
        var cols = "";

        cols += '<td class="col-5"><input type="text" class="form-control"  name="descriptionLine' + nextRowId + '"/></td>';
        cols += '<td class="col-2"><input type="text" class="form-control" id="price' + nextRowId + '"   name="priceLine' + nextRowId + '" onkeyup="calculateTotal('+nextRowId+')"/></td>';
        cols += '<td class="col-1"><input type="text" class="form-control" id="quantity'+nextRowId+'"  name="quantityLine' + nextRowId + '" onkeyup="calculateTotal('+nextRowId+')"/></td>';
        cols += '<td class="col-2"><input type="text" class="form-control line-total" id="total'+nextRowId+'"  name="totalLine' + nextRowId + '"/></td>';

        cols += '<td class="col-2"><input type="button" class="ibtnDel btn btn-md btn-danger btn-block"  value="Delete"></td>';
        
	newRow.append(cols);
        $("table.order-list").append(newRow);
        
    });



    $("table.order-list").on("click", ".ibtnDel", function (event) {
        $(this).closest("tr").remove();       
   });

    
    $("#org-form").on("click", ".add-zip", function (event) {

        newCount = $("zipSection").children().length + 1;

	var newZipRow = '<div class="form-group row">' +
            	           '<label for="targetZip' + newCount + '" class="col-sm-2 col-form-label">Target Zip</label>' +
                           '<div class="col-sm-2">' +
		             '<input type="text" class="form-control" id="targetZip' + newCount + '" name="targetZip' + newCount + '">' +
                           '</div>' +
	                   '<label for="radius' + newCount + '" class="col-sm-2 col-form-label">Radius (Miles)</label>' +
	                   '<div class="col-sm-2">' +
		             '<input type="text" class="form-control" id="radius' + newCount + '" name="radius' + newCount + '">' +
	                   '</div>' +
	                   '<div class="col-sm-2">' +
		             '<input type="button" class="btn btn-primary btn-block add-zip" value="Add Zip">' +
	                   '</div>' +
                         '</div>';     

       $("#zipSection").append(newZipRow);

       $("#zipSection div:nth-last-child(2)").find(".add-zip").addClass("btn-danger").addClass("remove-zip").removeClass("btn-primary").removeClass("add-zip").val("Remove")


    });

   $("#org-form").on("click", ".remove-zip",function (event) {
        $(this).parent().parent().remove();
   }); 


});


function calculateTotal(rowId) {

   quantityElem = document.getElementById("quantity"+rowId.toString())
   priceElem = document.getElementById("price"+rowId)
   totalElem = document.getElementById("total"+rowId)

   total = parseFloat(priceElem.value) * parseFloat(quantityElem.value)

   totalElem.innerText = total || 0
   totalElem.value = total || 0

   findTotal()

}

function findTotal(){

    var arr = document.getElementsByClassName('line-total');
    var tot=0;
    for(var i=0;i<arr.length;i++){

        if(parseFloat(arr[i].value))
            tot += parseFloat(arr[i].value);
    }

    console.log(tot)

    document.getElementById('estimate').value = tot;
    document.getElementById('estimate').innerText = tot;
}
