# Snoredex card links with YOURLS

The card ID and its public keyword are kept together in `data/social.json`. The keyword should remain
the same even when the site moves. Keep the YOURLS server's database backed up so that its existing
links can be restored.

Use the local planner for a configured printing:

```console
python scripts/yourls_cards.py item-bbea2621-c8f4-5647-b576-e309aa29d24a
```

This mode uses local data only and prints the proposed keyword, card URL and approved preview URL.
The suggested lowercase keyword is based on the stable item ID. Once the card and preview are publicly
available, pass `--check` to check an existing keyword, or `--create` to create an unused one. Those modes
read the YOURLS API signature from the local process environment as `SNOREDEX_YOURLS_SIGNATURE`.
Use the protected workflow below for the hosted pilot. Local planning needs no signature.

The script confirms an exact destination through `expand` and refuses a keyword that points elsewhere.
It verifies the deployed page metadata and preview bytes before creating a link. A verified result
also reports the public HTTP redirect status. This public request can be counted as a visit by YOURLS.
Record the verified keyword as `shortAlias` on the same item before generating its Instagram caption.
The script prints a result and leaves the catalogue record to review.

## Protected pilot workflow

Configure the GitHub Environment `yourls-pilot` **before** adding credentials. Set its deployment
policy to **Selected branches and tags**, add an exact **branch** rule for `main`, leave tags out,
and leave **Required reviewers** off so each run can finish automatically. Do this in GitHub
settings even though the workflow checks its ref. Scope the dedicated YOURLS signature to the
environment secret `SNOREDEX_YOURLS_SIGNATURE`. Keep the signature out of the repo, PRs, chat and
artifacts.
The core YOURLS signature grants broad API access. The workflow boundary and its reviewed code
limit which operations the pilot performs.

Run **Provision Snoredex short links** from `main` using the GitHub Actions UI or workflow dispatch
API. The job accepts one to three space-separated item IDs from the catalogue. Leave `request` empty: the photo inbox's intake run sets it to find its own run (#673). The photo
inbox's intake run starts it for every newly filed owner photo.

The pilot is done: SPEC-0774 alone, then the two CSV7C variants in one batch and again in reverse
order, gave stable assignments, and all three aliases are recorded in `data/social.json`. They stay
the worked examples:

| Pilot | Item ID |
|---|---|
| SPEC-0774 | `item-bbea2621-c8f4-5647-b576-e309aa29d24a` |
| SPEC-0779 (Poke Ball) | `item-b26a638d-ed89-538b-ab49-a5c879572f60` |
| SPEC-0780 (Master Ball) | `item-a2f8335e-94ff-54d2-8b10-5bdf55349451` |

Read the `yourls-verified` artifact. Only a fully verified result may enter `data/social.json`.
Record each `shortAlias` under its exact `itemId` in a reviewed data change. The job leaves GitHub
content unchanged. If a later item fails after an earlier alias was created, fix the reported
condition and rerun the batch. Existing correct aliases are read back and reused. A timeout
or duplicate response triggers a read of the exact keyword before another attempt. The job
never renames, deletes or retargets an existing alias.

[GitHub Environment branch rules and secrets](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)

## Moving the site

First test the migration with a disposable keyword. Record the old destination, verify that the new
page and preview show the same printing, and edit only the destination in YOURLS Admin. Then check
the original keyword in a fresh browser and in one that previously followed it. Also check the share
preview in the target app.

YOURLS uses 301 redirects by default. A client may retain that old destination after an admin edit.
For links that must remain movable, check the installation's actual redirect status and cache headers
before using them in posts. If a temporary redirect is needed, use a YOURLS plugin or a correctly
scoped server rule for Snoredex keywords. If destination changes later become a recurring task,
prefer a narrow authenticated plugin action using YOURLS's link-edit function. Require the old
destination, maintain the same keyword, and verify the result before distributing it.

[Standard YOURLS API](https://yourls.org/docs/guide/advanced/api) ·
[Plugin hooks](https://yourls.org/docs/development/plugins) ·
[Default redirect and redirect hook](https://github.com/YOURLS/YOURLS/blob/master/includes/functions.php) ·
[Link edit and cache handling](https://github.com/YOURLS/YOURLS/blob/master/includes/functions-shorturls.php)
