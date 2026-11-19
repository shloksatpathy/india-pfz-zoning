# Fishing harbours: name -> (lat, lon, region in regions.REGIONS)
# Yanam is part of Puducherry but lies on the Andhra Pradesh coast.
# Names: Handbook on Fisheries Statistics 2020, Department of Fisheries, Govt. of India
#   (Table 13.2 major fishing harbours, Table 13.3 fishing harbours "FH" commissioned till 2019-20;
#   Lakshadweep has no FH, so its fish landing centres are used).
# Coordinates: OpenStreetMap via Nominatim, © OpenStreetMap contributors, ODbL.
HARBOURS = {
    # Gujarat
    "Veraval": (20.9101, 70.3653, "Gujarat"),
    "Mangrol": (21.1242, 70.1199, "Gujarat"),
    "Porbandar": (21.6505, 69.6565, "Gujarat"),
    "Jakhau": (23.2198, 68.7142, "Gujarat"),
    # Maharashtra
    "Mumbai (Sassoon Dock)": (18.9144, 72.8242, "Maharashtra & Goa"),
    "Ratnagiri": (17.2826, 73.4570, "Maharashtra & Goa"),
    # Karnataka
    "Karwar": (14.8122, 74.1323, "Karnataka & Kerala"),
    "Honnavar": (14.3159, 74.4324, "Karnataka & Kerala"),
    "Tadri": (14.5254, 74.3536, "Karnataka & Kerala"),
    "Mangaluru": (12.8698, 74.8430, "Karnataka & Kerala"),
    "Malpe": (13.3507, 74.7037, "Karnataka & Kerala"),
    "Gangolli": (13.6528, 74.6704, "Karnataka & Kerala"),
    # Kerala
    "Kochi": (9.9395, 76.2607, "Karnataka & Kerala"),
    "Vizhinjam": (8.3818, 76.9916, "Karnataka & Kerala"),
    "Puthiyappa": (11.3212, 75.7463, "Karnataka & Kerala"),
    "Munambam": (10.1821, 76.1720, "Karnataka & Kerala"),
    "Neendakara": (8.9429, 76.5386, "Karnataka & Kerala"),
    "Chombal": (11.6776, 75.5521, "Karnataka & Kerala"),
    "Mopla Bay": (11.8565, 75.3758, "Karnataka & Kerala"),
    "Thangassery": (8.8817, 76.5685, "Karnataka & Kerala"),
    "Muthalapozhi": (8.6309, 76.7860, "Karnataka & Kerala"),
    "Kayamkulam": (9.1724, 76.5001, "Karnataka & Kerala"),
    "Thottappally": (9.3188, 76.3848, "Karnataka & Kerala"),
    "Ponnani": (10.7801, 75.9189, "Karnataka & Kerala"),
    # Lakshadweep
    "Kavaratti": (10.5672, 72.6395, "Lakshadweep"),
    "Minicoy": (8.2952, 73.0648, "Lakshadweep"),
    "Agatti": (10.9479, 72.3177, "Lakshadweep"),
    # Tamil Nadu
    "Chennai (Kasimedu)": (13.1254, 80.2956, "Tamil Nadu & Puducherry"),
    "Thoothukudi": (8.8053, 78.1453, "Tamil Nadu & Puducherry"),
    "Mallipattinam": (10.2799, 79.3178, "Tamil Nadu & Puducherry"),
    "Kodiyakkarai": (10.2845, 79.8238, "Tamil Nadu & Puducherry"),
    "Vellapallam": (10.5214, 79.8384, "Tamil Nadu & Puducherry"),
    "Thondi": (9.7423, 79.0176, "Tamil Nadu & Puducherry"),
    "Chinna Muttom": (8.0937, 77.5620, "Tamil Nadu & Puducherry"),
    "Thengapattinam": (8.2387, 77.1731, "Tamil Nadu & Puducherry"),
    "Colachel": (8.1753, 77.2519, "Tamil Nadu & Puducherry"),
    "Mookaiyur": (9.1317, 78.4787, "Tamil Nadu & Puducherry"),
    # Puducherry
    "Puducherry": (11.9341, 79.8306, "Tamil Nadu & Puducherry"),
    "Karaikal": (10.9157, 79.8376, "Tamil Nadu & Puducherry"),
    "Yanam": (16.7385, 82.2106, "Andhra Pradesh"),
    # Andhra Pradesh
    "Visakhapatnam": (17.6936, 83.2921, "Andhra Pradesh"),
    "Kakinada": (16.9437, 82.2351, "Andhra Pradesh"),
    "Nizampatnam": (15.9046, 80.6668, "Andhra Pradesh"),
    "Bhavanapadu": (18.5709, 84.3540, "Andhra Pradesh"),
    "Machilipatnam": (16.1817, 81.1348, "Andhra Pradesh"),
    # Odisha
    "Paradip": (20.2869, 86.6740, "Odisha & West Bengal"),
    "Gopalpur": (19.2599, 84.9052, "Odisha & West Bengal"),
    "Dhamra": (20.7956, 86.9010, "Odisha & West Bengal"),
    "Astaranga": (19.9784, 86.3099, "Odisha & West Bengal"),
    # West Bengal
    "Fraserganj": (21.5825, 88.2583, "Odisha & West Bengal"),
    "Digha": (21.6231, 87.5083, "Odisha & West Bengal"),
    "Sultanpur (Diamond Harbour)": (22.1669, 88.2005, "Odisha & West Bengal"),
    "Kakdwip (Harwood Point)": (21.8611, 88.2466, "Odisha & West Bengal"),
    # Andaman & Nicobar
    "Port Blair (Phoenix Bay)": (11.6729, 92.7343, "Andaman & Nicobar"),
}
