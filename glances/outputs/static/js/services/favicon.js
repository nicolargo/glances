
import Favico from 'favico.js';

export default angular.module('glancesApp').service('favicoService', favicoService);

function favicoService () {

    var favico = new Favico({
        animation: 'none'
    });

    this.badge = function (nb) {
        favico.badge(nb);
    };

    this.reset = function () {
        favico.reset();
    };
}