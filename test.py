from tools import lookup_plant, get_seasonal_conditions

# 测试1：alias 匹配
r1 = lookup_plant("devil's ivy")
print('Test 1 (alias):', r1['found'], '-', r1['plant']['display_name'])

# 测试2：大写输入
r2 = lookup_plant('SNAKE PLANT')
print('Test 2 (caps):', r2['found'], '-', r2['plant']['display_name'])

# 测试3：不存在的植物
r3 = lookup_plant('bird of paradise')
print('Test 3 (not found):', r3['found'], '-', r3['message'])