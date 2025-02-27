from d4explorer.datastore import preprocess


def test_preprocess(d4file, gff):
    s1 = d4file("s1")
    data = preprocess(str(s1), annotation=str(gff))
    # print(type(data))
    # print(type(data.data))
    print(data.regions.keys())
    print(data.regions["genome"])
    # print(data.regions_asdf)
