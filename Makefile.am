## Process this file with automake to produce Makefile.in
## Created by Anjuta

SUBDIRS = src 

glancesdocdir = ${prefix}/doc/glances
glancesdoc_DATA = \
	README\
	COPYING\
	AUTHORS\
	ChangeLog\
	INSTALL\
	NEWS


EXTRA_DIST = $(glancesdoc_DATA)


# Remove doc directory on uninstall
uninstall-local:
	-rm -r $(glancesdocdir)
