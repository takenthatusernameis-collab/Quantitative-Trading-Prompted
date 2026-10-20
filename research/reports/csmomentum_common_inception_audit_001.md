# CSMomentum Common-Inception Audit (Cycle 905)

```json
{
  "candidate": "csmomentum_001",
  "universe_size": 18,
  "common_inception": "2006-02-06",
  "union": {
    "start": "1993-01-29",
    "end": "2026-10-19",
    "sessions": 8488,
    "price_width_min": 1,
    "price_width_max": 18,
    "price_width_changes": [
      {
        "date": "1998-12-22",
        "assets_with_price": 10
      },
      {
        "date": "1999-03-10",
        "assets_with_price": 11
      },
      {
        "date": "2000-05-26",
        "assets_with_price": 12
      },
      {
        "date": "2001-08-27",
        "assets_with_price": 13
      },
      {
        "date": "2002-07-30",
        "assets_with_price": 14
      },
      {
        "date": "2003-04-14",
        "assets_with_price": 15
      },
      {
        "date": "2004-09-29",
        "assets_with_price": 16
      },
      {
        "date": "2004-11-18",
        "assets_with_price": 17
      },
      {
        "date": "2006-02-06",
        "assets_with_price": 18
      }
    ]
  },
  "common_inception_slice": {
    "start": "2006-02-06",
    "end": "2026-10-19",
    "sessions": 5208,
    "price_width_min": 18,
    "price_width_max": 18,
    "fully_populated": true
  },
  "common_inception_window": {
    "start": "2006-02-06",
    "end": "2026-10-19",
    "sessions": 5208,
    "note": "warm-up preserved variant; same window as slice"
  },
  "raggedness": {
    "union_price_width_changes": [
      {
        "date": "1998-12-22",
        "assets_with_price": 10
      },
      {
        "date": "1999-03-10",
        "assets_with_price": 11
      },
      {
        "date": "2000-05-26",
        "assets_with_price": 12
      },
      {
        "date": "2001-08-27",
        "assets_with_price": 13
      },
      {
        "date": "2002-07-30",
        "assets_with_price": 14
      },
      {
        "date": "2003-04-14",
        "assets_with_price": 15
      },
      {
        "date": "2004-09-29",
        "assets_with_price": 16
      },
      {
        "date": "2004-11-18",
        "assets_with_price": 17
      },
      {
        "date": "2006-02-06",
        "assets_with_price": 18
      }
    ],
    "sessions_with_fewer_than_N_assets_union": 3280
  },
  "checks": [
    {
      "name": "common_inception_rederived",
      "pass": true
    },
    {
      "name": "ci_after_union_start",
      "pass": true
    },
    {
      "name": "ci_index_nonempty",
      "pass": true
    },
    {
      "name": "common_inception_fully_populated",
      "pass": true
    }
  ],
  "overall": "PASS"
}
```
