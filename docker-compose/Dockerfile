FROM glances:local-alpine-minimal as glancesminimal
COPY glances.conf /glances/conf/glances.conf
CMD python -m glances -C /glances/conf/glances.conf $GLANCES_OPT
