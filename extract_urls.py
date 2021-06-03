import os
import sys
import json
import re

# This works for files of the type:
# - upgrade.jsonlz4-YYYYMMDDHHMMSS
# - previous.jsonlz4
# They first need to be decompressed using lz4json: https://unix.stackexchange.com/a/338880


# Count size, and optionally print structure
def count_size(obj, level=0, verbose=False):
    count = 0
    if isinstance(obj, list):
        if verbose: print()
        for i, e in enumerate(obj):
            if verbose: print("\t" * level, "i=", i, ", type=", type(e), end='')
            size = count_size(e, level + 1, verbose)
            count += size
    elif isinstance(obj, dict):
        if verbose: print()
        for key in obj.keys():
            if verbose: print("\t" * level, "key=", key, ", type=", type(obj[key]), end='')
            size = count_size(obj[key], level + 1, verbose)
            count += size
    else:  # Do not count the sizes of dict and lists as we already count the size of their items
        count += sys.getsizeof(obj)
        if verbose: print(", size=", count)
    return count


# Count total size and key-wise size, and optionally print structure
def count_size_per_key(obj, level=0, verbose=False):
    count_dict = {"total": 0}
    if isinstance(obj, list):
        if verbose: print()
        for i, e in enumerate(obj):
            if verbose: print("\t" * level, "i=", i, ", type=", type(e), end='')
            cdict = count_size_per_key(e, level + 1)
            for k in cdict:
                if k in count_dict:
                    count_dict[k] += cdict[k]
                else:
                    count_dict[k] = cdict[k]
    elif isinstance(obj, dict):
        if verbose: print()
        for key in obj.keys():
            if verbose: print("\t" * level, "key=", key, ", type=", type(obj[key]), end='')
            cdict = count_size_per_key(obj[key], level + 1)
            for k in cdict:
                if k in count_dict:
                    count_dict[k] += cdict[k]
                else:
                    count_dict[k] = cdict[k]
            if key in count_dict:
                count_dict[key] += cdict["total"]
            else:
                count_dict[key] = cdict["total"]
    else:  # Do not count the sizes of dict and lists as we already count the size of their items
        count_dict["total"] += sys.getsizeof(obj)
        if verbose: print(", size=", count_dict["total"])
    return count_dict


def print_session_info(A, tablevel=0, verbose=True, exploreNestedSessions=False, exploreClosedTabs=True,
                       only_last_entry=True, printOpenTabs=True, printClosedTabs=False):
    """
    Recursive function that takes a firefox session, prints its (potentially nested) structure, and returns urls found
    This doesn't explore closed windows.

    :param A: dict, with keys "windows,
    :param tablevel: used in printing to indicate nesting
    :param verbose: print the structure
    :param exploreNestedSessions: Firefox will nest sessions in tab entry (don't know why) so set to True to explore them
    :param exploreClosedTabs: Whether to explore "closed" tabs. Exploring means storing their urls.
    :param only_last_entry: allow to only get the last page that I visited in a particular tab
    :param printOpenTabs: print "opened" tabs and their urls
    :param printClosedTabs: print "closed" tabs and their urls
    :return:
    """
    opened_urls = []
    all_urls = []
    indent = "||--" * tablevel
    if verbose: print(indent, "The session contains:")
    if verbose: print(indent, "- %d windows" % len(A["windows"]))
    if verbose: print(indent, "- %d closed windows" % len(A["_closedWindows"]))
    if verbose: print(indent, )
    for i, w in enumerate(A["windows"]):
        if verbose: print(indent,
                          "Window %d: %d open tabs, %d closed tabs" % (i, len(w["tabs"]), len(w["_closedTabs"])))
        if verbose and printOpenTabs: print(indent, "Open tabs:")

        for j, t in enumerate(w["tabs"]):
            if verbose and printOpenTabs: print(indent, "\t- tab %d : %d entries" % (j, len(t["entries"])))
            for k, e in enumerate(t["entries"]):
                if not (only_last_entry and k < len(t["entries"]) - 1):
                    if verbose and printOpenTabs: print(indent, "\t\t", e["url"])
                    opened_urls.append(e["url"])
                    all_urls.append(e["url"])
            if exploreNestedSessions and "formdata" in t:
                if "id" in t["formdata"]:
                    if "sessionData" in t["formdata"]["id"]:
                        print(indent, "New session in window", i, ", tab", j, ":")
                        ou, au = print_session_info(t["formdata"]["id"]["sessionData"], tablevel + 1, verbose,
                                                    exploreNestedSessions, exploreClosedTabs,
                                                    only_last_entry, printOpenTabs, printClosedTabs)
                        opened_urls += ou
                        all_urls += ou
                        all_urls += au
        if exploreClosedTabs:
            if verbose and printClosedTabs: print(indent, "Closed tabs:")

            for j, t in enumerate(w["_closedTabs"]):
                if verbose and printClosedTabs: print(indent,
                                                      "\t- tab %d : %d entries" % (j, len(t["state"]["entries"])))
                for k, e in enumerate(t["state"]["entries"]):
                    if not (only_last_entry and k < len(t["state"]["entries"]) - 1):
                        if verbose and printClosedTabs: print(indent, "\t\t", e["url"])
                        opened_urls.append(e["url"])
                        all_urls.append(e["url"])
                if exploreNestedSessions and "formdata" in t:
                    if "id" in t["formdata"]:
                        if "sessionData" in t["formdata"]["id"]:
                            print(indent, "New session in window", i, ", tab", j, ":")
                            ou, au = print_session_info(t["formdata"]["id"]["sessionData"], tablevel + 1, verbose,
                                                        exploreNestedSessions, exploreClosedTabs,
                                                        only_last_entry, printOpenTabs, printClosedTabs)
                            opened_urls += ou
                            all_urls += ou
                            all_urls += au
    return opened_urls, all_urls


if __name__ == "__main__":

    # f = sys.argv[1]
    # f = "session-firefox/sessionstore-backups/upgrade.jsonlz4-20210222142601.txt"
    f = "session-firefox/sessionstore-backups/previous.jsonlz4.txt"
    A = json.load(open(f))

    # Find
    openTabs, allTabs = print_session_info(A, exploreNestedSessions=True, printOpenTabs=True, printClosedTabs=False)

    # for t in sorted(set(openTabs)):
    #     print(t)

    # Find only first level of nested sessionData
    # A = A["windows"][0]["tabs"][0]["formdata"]["id"]["sessionData"]
    # openTabs, allTabs = print_session_info(A, printOpenTabs=True, printClosedTabs=False, exploreNestedSessions=False)

    # # If file is corrupted (non-valid json), then this will find all urls independently of any structure.
    # # This gets all urls, even those of closed tabs
    # txt = open(f).read()
    # url_search = re.findall('"url":"(http.*?)"', txt, re.IGNORECASE)
    # url_list = list(set(url_search))  # Remove duplicates
    #
    # re.findall('"entries".*?"url":"(http.*?)"', txt, re.IGNORECASE) # Only the urls that have an "entries" tag before
    # re.findall('"url":"(http.*?)".*?"entries"', txt, re.IGNORECASE) # Only the urls that have an "entries" tag before
    # T = re.sub('"(?:[^"]*_base64|csp|image|value|referrerInfo|structuredCloneState)":".*?",',"",txt) # Remove long parts (binary data)

    # Get size (in bytes) of the different elements in the file
    # cnts = count_size(A,verbose=True)
    # print(cnts)
    # cntspk = count_size_per_key(A,verbose=True)
    # print(cntspk)
    # Get largest
    # sorted_order = sorted(cntspk.items(), key=lambda x: x[1], reverse=True)
    # [print(x) for x in sorted_order[:20]]


