$(function() {
    $(".slider").slick({
        dots: true,
        infinite: true,
        speed: 300,
        slidesToShow: 1,
        autoplay: true,
        arrows: false
    });

    $('.navbar-nav a').smoothScroll({
        offset: -50
    });
});
