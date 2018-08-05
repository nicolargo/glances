
export default function GlancesHelpController($http) {
    var vm = this;

    $http.get('api/3/help').then(function (response) {
        vm.help = response.data;
    });
}
