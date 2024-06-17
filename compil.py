import lark
import re
import math
import sys
import subprocess
#ON A TOUT MIS EN .BSS SUR CETTE VERSION
#Définition grammaire
#Tokens => capitalized, tree leaves | Rules => regular
grammaire = """%import common.SIGNED_NUMBER
%import common.WS
%ignore WS
VARIABLE : /[a-su-zA-Z_][a-zA-Z_0-9]*/
TVARIABLE : /t[a-zA-Z_0-9]*/
NOMBRE : SIGNED_NUMBER
// auparavant /[1-9][0-9]*/ mais manquait Z et 0
OPBINAIRE : /[+*\/&><]/|">="|"-"|"<="|">>"
expression : VARIABLE -> exp_variable 
    |NOMBRE -> exp_nombre 
    |expression OPBINAIRE expression -> exp_binaire

    |"len" "(" TVARIABLE ")" -> tab_length
    |TVARIABLE "[" expression "]" -> tab_value

commande : VARIABLE "=" expression ";" -> com_asgt
    |"printf" "(" expression ")" ";" -> com_printf
    |commande+ -> com_sequence
    |"while" "(" expression ")" "{" commande "}" -> com_while
    |"if" "(" expression ")" "{" commande "}" "else" "{" commande "}" -> com_if

    |"var" TVARIABLE "[" expression "]" ";" -> tab_decl
    |TVARIABLE "[" expression "]" "=" expression ";" -> tab_index_affect

liste_var : -> liste_vide | VARIABLE ("," VARIABLE)* -> liste_normale
programme : "main" "(" liste_var ")" "{" commande "return" "(" expression ")" ";" "}"
"""

#Parser
parser = lark.Lark(grammaire, start = "programme")

#Parsing with Earley's algorithm by default (LALR...)
tree = parser.parse("""
                    main(X, Y) {
                       var tX[10];
                       while (X) {
                            X = X - 1;
                            Y = Y + 1;
                            tX[1] = 1;
                       }
                        if (Y) {
                            printf(Y);
                        } else {
                            X = tX[Y];
                            printf(len(tX));
                        }
                    return(Y);
                    }
                    """)

tree2 = parser.parse("""
                    main(X, Y) {
                        var tX[X];
                        printf(len(tX));
                        tX[1] = 1;
                        printf(tX[1]);
                        X = tX[Y];
                        printf(X);
                        return(len(tX));
                    }
                    """)
#data attribute: rule
#children attribute: list of children
#value attribute : value of a Token
#type attribute: token type


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

#to ASM
#argv 0 contient le nom du programme
#nasm -f elf64 fichier.asm
# gcc -no-pie fichier.o
# ./a.out argv

global counter
counter = 0

def toASM(tree):
    variableSet, arraySet = countVariables(tree)
    return """extern printf, atoi, malloc
global main
    
section .data
long_format: db "%%lld", 10, 0 ; 10 a la ligne 
argc: dq 0
argv: dq 0
%s

section .bss
%s

section .text 
main:
; opening
%s
; initialisation des variables de main 
%s
; body 
%s 
; return
%s
; closing 
%s""" % (toASMVariable(variableSet), toASMBSS(arraySet), getOpening(), toASMMainVariable(tree.children[0]), toASMCommand(tree.children[1]), toASMReturn(tree.children[2]), getClosing())

def countVariables(tree):
    variableSet = set()
    arraySet = set()
    if tree.children[0].data == "liste_normale":
        for variableToken in tree.children[0].children:
            variableSet.add(variableToken.value)

    def countRec(tree):
        for child in tree.children:
            if type(child) == lark.Tree :
                if child.data == "com_asgt":
                    variableSet.add(child.children[0].value)
                elif child.data == "tab_decl":
                    arraySet.add(child.children[0].value)
                countRec(child)
                
    countRec(tree)
    return variableSet, arraySet


def getOpening():
    return """push rbp ; Set up the stack. Save rbp
mov rbp, rsp
mov [argc], rdi
mov [argv], rsi
"""

def toASMReturn(tree):
    #TODO MODIFIER SANS RETOUR A LA LIGNE
    return """%s
mov rdi, long_format
mov rsi, rax
xor rax, rax
call printf
""" % toASMExpression(tree)

def getClosing():
    return """pop rbp
xor rax, rax
ret"""

def toASMExpression(tree):
    #TODO PAS TOUT METTRE DANS RAX
    #TODO add binary operators
    if tree.data == "exp_nombre":
        #Traiter dans python, init tableau et pointeur dans rax
        return "mov rax, %s" % tree.children[0].value
    elif tree.data == "exp_variable":
        #Enlever []?
        return "mov rax, [%s]" % tree.children[0].value
    elif tree.data == "exp_binaire":
        return """%s
push rax
%s
pop rbx
%s
""" % (toASMExpression(tree.children[2]), toASMExpression(tree.children[0]), toASMOpBinaire(tree.children[1]))
    elif tree.data == "tab_length":
        return "mov rax, [%s_size]" % tree.children[0].value
    elif tree.data == "tab_value":
        return f"""
{toASMExpression(tree.children[1])}
imul rax, 8
mov rbx, [{tree.children[0].value}_pointer + rax]
mov rax, rbx
"""
    else: 
        print("error in toASMExpression")

def toASMOpBinaire(tree):
    #TODO GERER LES CALCULS AVEC LES POINTEURS + REALLOUER DE LESPACE
    if tree.value == "+":
        return """add rax, rbx"""
    elif tree.value == "-":
        return """sub rax, rbx"""
    elif tree.value == "x" or tree.value == "*":
        return """mul rax, rbx"""
    else :
        print ("error in toASMOpBinaire")


def toASMCommand(tree):
    global counter
    if tree.data == "com_sequence":
        return "\n".join([toASMCommand(child) for child in tree.children])
    #Ne pas trop changer?
    elif tree.data == "com_asgt":
        print("test", tree)
        return """%s
mov [%s], rax
""" % (toASMExpression(tree.children[1]), tree.children[0].value)
    #PRINTF SANS SAUTER DE LIGNE
    elif tree.data == "com_printf":
        return """%s
mov rdi, long_format
mov rsi, rax
xor rax, rax
call printf
""" % toASMExpression(tree.children[0])
    elif tree.data == "com_while":
        counter += 1
        return f"""debut_{counter}: {toASMExpression(tree.children[0])}
cmp rax, 0
jz fin_{counter}
{toASMCommand(tree.children[1])}
jmp debut_{counter}
fin_{counter}: nop
"""
    elif tree.data == "com_if":
        counter += 1
        return f"""{toASMExpression(tree.children[0])}
cmp rax, 0
jz fin_{counter}
{toASMCommand(tree.children[1])}
fin_{counter}: {toASMCommand(tree.children[2])}
"""
    elif tree.data == "tab_decl":
        return """%s 
mov [%s_size], rax
mov rdi, rax
imul rdi, 8
call malloc
mov [%s_pointer], rax
""" % (toASMExpression(tree.children[1]), tree.children[0].value, tree.children[0].value)
    elif tree.data == "tab_index_affect":                                              
        return f"""{toASMExpression(tree.children[2])}
mov rbx, rax
{toASMExpression(tree.children[1])}
imul rax, 8
mov qword [{tree.children[0].value}_pointer + rax], rbx
"""
    else:
        print("error in toASMCommand")


def toASMVariable(variableSet):
    res = ""
    if not variableSet == set():
        res +=  "\n".join(["%s: dq 0" % name for name in variableSet])
        res += "\n"
    return res

def toASMBSS(arraySet):
    res = ""    
    if not arraySet == set():
        res += "\n".join(["%s_size resq 1" % name for name in arraySet])
        res += "\n"
        res += "\n".join(["%s_pointer resq 1" % name for name in arraySet])
        res += "\n"
    return res
    
def toASMMainVariable(tree):
    #TODO GESTION DECOMPOSITION
    res = ""
    for i in range(len(tree.children)):
        res += """mov rbx, [argv]
mov rdi, [rbx + %d]
xor rax, rax
call atoi
mov [%s], rax
""" % (8*(i + 1), tree.children[i].value)
    return res

def save(filename, asm):
    with open(filename, "w") as file:
        file.write(asm)

#print(tree2)
#save("array.asm", toASM(tree2))
#print(pretty_printer_program(tree2))

def bigNumberToSize(n, base):
    return math.floor(math.log(n) / math.log(base)) + 1

def CtoC(script, base):
    result = []
    lines = script.split("\n")
    for line in lines:
        if re.match(r"[a-su-zA-Z_][a-zA-Z_0-9]*\s*=\s*.*", line):
            #Affectations
            components = line.split("=")
            number = components[2].replace(" ", "")
            name = components[0].replace(" ", "")
            size = number
            if number.isDigit():
                size = str(bigNumberToSize(int(number)))
            lines.append(f"var t__{name}[{size}]")
        if line.contains("+"):
            pass
            #Opérations binaires (+, -, x)
            #print
        else:
            result.append(line)
    return result.join("\n")

if __name__ == "__main__":
    filename = sys.argv[1]
    file = open(filename, 'r', encoding='utf-8')
    lines = file.read()
    tree_lines = parser.parse(lines)
    print(pretty_printer_program(tree_lines))
    print(filename)
    if len(sys.argv) == 3:
        name = sys.argv[2]
    else:
        name = filename.split(".")[0]
        name = name+"."+"ams"
    print(name)
    with open(name, 'w', encoding='utf-8') as file_out:
        file_out.write(toASM(tree_lines))
        result = subprocess.run(f"nasm -f elf64 {name}", capture_output=True, text=True)
        print(result)
        name = name.split(".")[0]
        name = name+".o"
        result = subprocess.run(f"gcc -no-pie {name}")
