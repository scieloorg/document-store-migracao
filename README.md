# Document Store (Kernel) - Migração


        # issues_id = requests.get(
        #     "%s/issue/identifiers/" % AM_URL_API,
        #     params={"collection": "spa", "issn": obj_journal.scielo_issn},
        # ).json()

        # print("ISSUES:", issues_id["meta"]["total"])
        # for d_issues in issues_id["objects"]:
        #     issue = requests.get(
        #         "%s/issue" % AM_URL_API,
        #         params={"collection": "spa", "code": d_issues["code"]},
        #     ).json()
        #     obj_issue = Issue(issue)