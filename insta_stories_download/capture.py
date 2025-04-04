from instacapture import InstaStory, InstaPost

cookies = {
    "ps_n": "1",
    "datr": "XDDkZzvGrBXR9Gc1EAqwhiK-",
    "ig_nrcb": "1",
    "ds_user_id": "73704269273",
    "csrftoken": "Q37jduXLFvzDxEYrIh5agAl2vTJNYN9d",
    "ig_did": "11E63A34-58D2-486B-8B0C-3270B5252FFE",
    "ps_l": "1",
    "wd": "1366x621",
    "mid": "Z-QwXgAEAAEVX5qNVBVCw-_wjvoF",
    "sessionid": "73704269273%3AEOW2hK9PpCQE84%3A20%3AAYdKdcqTL2VaY6VYsFsicS_FxbLVFvAyBhdNRe_W9w",
    "rur": "\"NHA\\05473704269273\\0541775046871:01f7d9045704dcae94cfff1cff61c3bcaf44e0be2babc6d8094b2898b1ba92ab0fe1ceda\""
}


story_obj = InstaStory()
story_obj.cookies = cookies

story_obj.username = 'virginia'
story_obj.story_download()

# story_obj.username = 'Enter username or profile link'
# story_obj.story_download()
