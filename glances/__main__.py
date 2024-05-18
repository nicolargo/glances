#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Allow user to run Glances as a module."""

# Execute with:
# $ python -m glances (2.7+)

import glances

if __name__ == '__main__':
    glances.main()
