#PRETTY PRINTER

def pretty_printer_program(tree):
    return "main (%s) {\n%s\nreturn(%s);\n}" % (pretty_printer_listVar(tree.children[0]), 
                                             pretty_printer_command(tree.children[1]), 
                                             pretty_printer_expression(tree.children[2]))

def pretty_printer_listVar(tree):
    if tree.data == "liste_vide":
        return ""
    else:
        return ", ".join([child.value for child in tree.children])

def pretty_printer_command(tree):
    if tree.data == "com_sequence":
        return "\n".join([pretty_printer_command(child) for child in tree.children])
    elif tree.data == "com_asgt":
        return tree.children[0].value + " = " + pretty_printer_expression(tree.children[1]) + ";"
    elif tree.data == "com_printf":
        return "printf(" + pretty_printer_expression(tree.children[0])+ ");"
    elif tree.data == "com_while":
        return "while(%s){\n%s\n}" % (pretty_printer_expression(tree.children[0]), pretty_printer_command(tree.children[1]))
    elif tree.data == "com_if":
        return "if(%s){\n%s\n} else {\n%s\n}" % (pretty_printer_expression(tree.children[0]), pretty_printer_command(tree.children[1]), pretty_printer_command(tree.children[2]))
    elif tree.data == "tab_decl":
        return "var %s[%s];" % (tree.children[0].value, pretty_printer_expression(tree.children[1]))
    elif tree.data == "tab_index_affect":
        return "%s[%s] = %s" % (tree.children[0].value, pretty_printer_expression(tree.children[1]), pretty_printer_expression(tree.children[2]))
    else:
        print("error in pretty printer command")

def pretty_printer_expression(tree):
    if tree.data == "exp_nombre" or tree.data == "exp_variable":
        return tree.children[0].value
    elif tree.data == "exp_binaire":
        return pretty_printer_expression(tree.children[0]) + " " + tree.children[1].value + " " + pretty_printer_expression(tree.children[2])
    elif tree.data == "tab_length":
        return "len(%s)" % tree.children[0].value
    elif tree.data == "tab_value":
        return "%s[%s]" % (tree.children[0].value, pretty_printer_expression(tree.children[1]))
    else: 
        print("error in pretty printer expression")
