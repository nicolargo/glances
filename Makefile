MSGFMT = msgfmt -v

.SUFFIXES: .po .mo

MSGOBJ := $(patsubst %.po,%.mo,$(wildcard i18n/*/LC_MESSAGES/*.po))

.po.mo:
	$(MSGFMT) -o $@ $<

all: $(MSGOBJ)
