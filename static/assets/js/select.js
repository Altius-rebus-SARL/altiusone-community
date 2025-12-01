//select js

$(function() {
    $('.select-1').select2();
});
$(function() {
    $('.select-example').select2();
});
$(function() {
    $('.select-example-two').select2();
});
$(function() {
    $('.select-basic-multiple-four').select2();
});
$(".select-example-rtl").select2({
    dir: "rtl"
  });
$(".js-example-disabled").select2();
$(".select-basic-multiple-five").select2();
$(".select-basic-multiple-seven").on("click", function () {
  $(".js-example-disabled").prop("disabled", false);
  $(".select-basic-multiple-five").prop("disabled", false);
});
$(".select-basic-multiple-six").on("click", function () {
  $(".js-example-disabled").prop("disabled", true);
  $(".select-basic-multiple-five").prop("disabled", true);
});
$('.select2-icon').select2({
    width: "100%",
});
$('.select2-icons').select2({
    width: "100%",
});

// ✅ AJOUTER CES LIGNES POUR NOS FORMULAIRES
$(function() {
    // Select2 avec recherche
    if ($('.select2').length > 0) {
        $('.select2').select2({
            placeholder: "Sélectionnez...",
            allowClear: true,
            width: "100%"
        });
    }
    
    // Select basic sans recherche
    if ($('.select-basic').length > 0) {
        $('.select-basic').select2({
            minimumResultsForSearch: Infinity,
            width: "100%"
        });
    }
});
