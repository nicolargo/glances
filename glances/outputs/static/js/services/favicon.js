
import angular from "angular";
import Favico from "favico.js";

function favicoService () {

    var favico = new Favico({
        animation: "none"
    });

    this.badge = function (nb) {
        favico.badge(nb);
    };

    this.reset = function () {
        favico.reset();
    };
}

export default angular.module("glancesApp").service("favicoService", favicoService);
