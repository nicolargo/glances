glancesApp.service('favicoService', function() {

  var favico = new Favico({
    animation : 'none'
  });

  this.badge = function(nb) {
    favico.badge(nb);
  };

  this.reset = function() {
    favico.reset();
  };
});
