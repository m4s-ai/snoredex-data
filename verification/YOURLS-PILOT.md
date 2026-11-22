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
Set it only in the Homelab environment used for this task. The signature belongs in the authenticated
YOURLS administration, the process environment, or the Homelab's secret store.

The script confirms an exact destination through `expand` and refuses a keyword that points elsewhere.
It verifies the deployed page metadata and preview bytes before creating a link. A verified result
also reports the public HTTP redirect status. This public request can be counted as a visit by YOURLS.
Record the verified keyword as `shortAlias` on the same item before generating its Instagram caption.
The script prints a result and leaves the catalogue record to review.

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
