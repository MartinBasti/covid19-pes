#!/usr/bin/env python3
# pes.py: plot PES score for COVID-19 epidemic from open data
# Copyright (C) 2020 Tomas Krizek
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from collections import defaultdict
from datetime import date, timedelta
import json
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


POPULATION = 10693939
POPULATION_SENIOR = 2131630
TESTS_NEW_GUESSTIMATE = 0.9  # assume 90% of tests are new tests (not re-tests)
PES_PERIOD = int(sys.argv[1])
SRC_LINK = "https://github.com/tomaskrizek/covid19-pes/releases/tag/v0.1.0"


with open('osoby.min.json') as f:
    in_people = json.load(f)

with open('testy.min.json') as f:
    in_tests = json.load(f)

cases_new = defaultdict(int)
cases_new_senior = defaultdict(int)
tests_new = defaultdict(int)

for entry in in_people['data']:
    date = date.fromisoformat(entry['datum'])
    cases_new[date] += 1

    if entry['vek'] >= 65:
        cases_new_senior[date] += 1

for entry in in_tests['data']:
    date = date.fromisoformat(entry['datum'])
    tests_new[date] = entry['prirustkovy_pocet_testu']

cases_inc_7d = defaultdict(int)
cases_inc_14d = defaultdict(int)
cases_inc_14d_senior = defaultdict(int)

for date, n in cases_new.items():
    for i in range(7):
        cases_inc_7d[date + timedelta(days=i)] += n
    for i in range(14):
        cases_inc_14d[date + timedelta(days=i)] += n

for date, n in cases_new_senior.items():
    for i in range(14):
        cases_inc_14d_senior[date + timedelta(days=i)] += n


tests_inc_7d = defaultdict(int)
for date, n in tests_new.items():
    for i in range(7):
        tests_inc_7d[date + timedelta(days=i)] += n


tests_since = sorted(tests_inc_7d.keys())[0] + timedelta(days=7)
tests_until = sorted(tests_inc_7d.keys())[-1]
cases_since = sorted(cases_inc_7d.keys())[0] + timedelta(days=7)
cases_until = sorted(cases_inc_7d.keys())[-1]
positivity_since = max(tests_since, cases_since)
positivity_until = min(tests_until, cases_until)

positivity_7d = {}
for i in range((positivity_until - positivity_since).days + 1):
    date = positivity_since + timedelta(days=i)
    positivity_7d[date] = cases_inc_7d[date] / (tests_inc_7d[date] * TESTS_NEW_GUESSTIMATE)


def score_pes_prevalence(prevalence):
    if prevalence < 10:
        return 0
    if prevalence < 25:
        return 2
    if prevalence < 50:
        return 4
    if prevalence < 120:
        return 7
    if prevalence < 240:
        return 10
    if prevalence < 480:
        return 13
    if prevalence < 960:
        return 16
    return 20


def score_pes_senior(prevalence_senior, prevalence_senior_prev):
    extra = 0 if prevalence_senior <= prevalence_senior_prev else 2
    if prevalence_senior < 10:
        return 0 + extra
    if prevalence_senior < 25:
        return 2 + extra
    if prevalence_senior < 50:
        return 4 + extra
    if prevalence_senior < 120:
        return 7 + extra
    if prevalence_senior < 240:
        return 10 + extra
    if prevalence_senior < 480:
        return 13 + extra
    if prevalence_senior < 960:
        return 16 + extra
    return 20 + extra


def score_pes_repro(repro):
    if repro < 0.8:
        return 0
    if repro < 1.0:
        return 5
    if repro < 1.2:
        return 10
    if repro < 1.4:
        return 15
    if repro < 1.6:
        return 20
    if repro < 1.9:
        return 25
    return 30


def score_pes_positivity(positivity, positivity_prev):
    extra = 0 if positivity <= positivity_prev else 2
    if positivity < 0.03:
        return 0 + extra
    if positivity < 0.07:
        return 3 + extra
    if positivity < 0.11:
        return 7 + extra
    if positivity < 0.15:
        return 11 + extra
    if positivity < 0.19:
        return 15 + extra
    if positivity < 0.23:
        return 20 + extra
    if positivity < 0.26:
        return 25 + extra
    return 30 + extra


since = max(sorted(cases_new.keys())[0], sorted(tests_new.keys())[0]) + timedelta(days=21)
until = min(sorted(cases_new.keys())[-1], sorted(tests_new.keys())[-1])

pes = {}
for i in range((until - since).days + 1):
    date = since + timedelta(days=i)
    repro = cases_inc_7d[date] / cases_inc_7d[date - timedelta(days=5)]
    prevalence = cases_inc_14d[date] / POPULATION * 100000
    prevalence_senior = cases_inc_14d_senior[date] / POPULATION_SENIOR * 100000
    prevalence_senior_prev = cases_inc_14d_senior[date - timedelta(days=7)] / POPULATION_SENIOR * 100000

    vals = (score_pes_prevalence(prevalence),
                 score_pes_senior(prevalence_senior, prevalence_senior_prev),
                 score_pes_repro(repro),
                 score_pes_positivity(positivity_7d[date],
                        positivity_7d[date - timedelta(days=7)]))

    pes[date] = (*vals, sum(vals))


x = []
for i in range(PES_PERIOD + 1):
    x.append(until - timedelta(days=(PES_PERIOD - i)))


y = list(pes[x][4] for x in x)

print(x)
print(y)


fig, ax = plt.subplots(1)

plt.title("PES (posledních {:d} dní k {:s})".format(PES_PERIOD, until.strftime("%d.%m.%Y")))
plt.xlabel("datum")
plt.ylabel("skóre rizika (PES)")

ax.set_ylim(0, 104)
ax.plot(x, y)

patches = [
    Rectangle((0, 0), 1, 20/104, transform=ax.transAxes, facecolor="forestgreen", alpha=0.4),
    Rectangle((0, 20/104), 1, 20/104, transform=ax.transAxes, facecolor="gold", alpha=0.4),
    Rectangle((0, 40/104), 1, 20/104, transform=ax.transAxes, facecolor="darkorange", alpha=0.4),
    Rectangle((0, 60/104), 1, 15/104, transform=ax.transAxes, facecolor="crimson", alpha=0.4),
    Rectangle((0, 75/104), 1, 29/104, transform=ax.transAxes, facecolor="indigo", alpha=0.4),
]

for patch in patches:
    ax.add_patch(patch)

fig.autofmt_xdate()
fig.text(0.02, 0.02, "{:s}".format(SRC_LINK), fontsize='xx-small', color='gray')
fig.text(0.95, 0.02, "CC0", fontsize='small', color='gray')

plt.savefig('pes_{:d}d_{:s}.png'.format(PES_PERIOD, str(until)), dpi=600)
