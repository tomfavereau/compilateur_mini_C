import lark
import math

#Définition grammaire
#Tokens => capitalized, tree leaves | Rules => regular
grammaire = """%import common.SIGNED_NUMBER
%import common.WS
%ignore WS
VARIABLE : /[ac-su-zA-Z_][a-zA-Z_0-9]*/
TVARIABLE : /t[a-zA-Z_0-9]*/
BIGVARIABLE : /b[a-zA-Z_0-9]*/
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
    | "big" BIGVARIABLE "=" expression ";" -> big_asgt
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
                        var tX[10];
                        printf(len(tX));
                        tX[1] = 1;
                        printf(tX[1]);
                        X = tX[3];
                        printf(X);
                        return(len(tX));
                    }
                    """)

tree3 = parser.parse("""
                    main(X){
                        X = 2;
                        return(0);
                    }
                    """)
#data attribute: rule
#children attribute: list of children
#value attribute : value of a Token
#type attribute: token type

#to ASM
#argv 0 contient le nom du programme
#nasm -f elf64 fichier.asm
# gcc -no-pie fichier.o
# ./a.out argv

global counter
counter = 0

def toASM(tree):
    variableSet, bigVariableSet, arraySet = countVariables(tree)
    return """extern printf, atoi, malloc, free
global main
    
section .data
long_format: db "%%lld", 10, 0 ; 10 a la ligne 
bigNumber_format: db "%%lld", 0
format: db "%%s", 10, 0
argc: dq 0
argv: dq 0
%s


section .bss
%s

section .text 


;------------------------------------    
;capacity, size, sign
;------------------------------------

;rdi = capacity
allocateBigNumber:
    push rbp
    imul rdi, 8
    call malloc ; Allocate memory
    mov qword [rax], rdi
    mov r9, rdi
    sub r9, 3
    mov qword [rax + 8], r9
    mov qword [rax + 16], 0 
    pop rbp
    ret

; rdi (variable 1), rsi (variable 2) 
movBig:
    push rbp
    mov rax, rdi
    mov rbx, rsi
    mov r9, qword [rax]
    sub r9, 3
    cmp r9, qword [rbx+8] ; on compare capacity et size

    jge .copy

    mov rdi, qword [rbx+8]
    add rdi, 3
    call malloc ; on écrase rax mais c'est pas grave
    mov r9, qword [rbx+8]
    mov qword [rax], r9
    add qword [rax], 3
    mov qword [rax+8], r9
    mov r9, qword [rbx+16]
    mov qword [rax+16], r9
    
    mov rcx, 3
.copy: 
    mov r9, qword [rbx+8*rcx]
    mov qword [rax+8*rcx], r9
    inc rcx
    
    mov r9, qword [rbx+8]
    add r9, 3
    cmp rcx, r9
    jl .copy
    pop rbp
    ret


 ;rdi, rsi
 big_number_same_sign:
    push rbp
    mov rbp, rsp
    ; Compare the sign parts at offset 16
    mov r9, qword [rsi + 16]
    cmp qword [rdi + 16], r9
    jne .not_equal

.equals:
    mov rax, 1
    jmp .done

.not_equal:
    mov rax, 0

.done:
    pop rbp
    ret

;rdi, rsi
big_number_cmp:
    push rbp
    mov r9, qword [rsi + 8]
    cmp qword [rdi + 8], r9
    jl .less
    jg .greater

    mov r14, 0
    mov r15, qword [rdi + 8]
    .loop:
        cmp r14, r15
        je .equals

        mov rax, r15             ; Charger r15 dans rax
        sub rax, 1               ; Soustraire 1 de rax
        sub rax, r14             ; Soustraire r14 de rax
        imul rax, rax, 8         ; Multiplier le résultat par 8 (taille de qword)
        add rax, rdi             ; Ajouter rdi pour obtenir l'adresse complète
        mov r8, qword [rax]      ; Charger la valeur à cette adresse dans r8

        mov rbx, r15             ; Charger r15 dans rbx
        sub rbx, 1               ; Soustraire 1 de rbx
        sub rbx, r14             ; Soustraire r14 de rbx
        imul rbx, rbx, 8         ; Multiplier le résultat par 8 (taille de qword)
        add rbx, rsi             ; Ajouter rsi pour obtenir l'adresse complète
        mov r9, qword [rbx]      ; Charger la valeur à cette adresse dans r9

        cmp r8, r9

        jl .less
        jg .greater
        inc r14
        jmp .loop
    
    .less:
    mov rax, -1
    jmp .done

    .greater:
    mov rax, 1
    jmp .done
    
    .equals:
    mov rax, 0
    
    .done:
    pop rbp
    ret

; Function to add two big numbers
; Input:
;   rdi: pointer to the first big number array
;   rsi: pointer to the second big number array
; Output:
;   rax: pointer to the result of the addition
big_number_add:
    push rbp
    ; Get pointers to the first and second big numbers
    mov rbx, rdi  ; Pointer to the first big number
    mov rcx, rsi  ; Pointer to the second big number
    
    ; Load capacities of the big numbers
    mov rdx, qword [rbx]  ; Capacity of the first big number
    sub rdx, 3
    mov r8, qword [rcx] ; Capacity of the second big number
    sub r8, 3
    
    ; Choose the maximum capacity for the result
    cmp rdx, r8
    jge .max_capacity_first
    mov rdx, r8

.max_capacity_first:
    
    ; Allocate memory for the result
    mov rdi, rdx  ; Capacity of the result
    add rdi, 3
    imul rdi, 8
    call malloc ; Allocate memory
    mov qword [rax], rdi
    
    ; Initialize carry to 0
    xor r9, r9
    
    ; Loop through the digits of the big numbers
    xor r10, r10  ; Initialize index to 0


    mov r11, rax
    mov rdi, rbx
    mov rsi, rcx
    call big_number_same_sign
    cmp rax, 1
    je .case_same_sign
    jne .case_diff_sign
    

.case_same_sign:
    mov r12, qword [rdi + 16]
    mov qword [r11 + 16], r12
    mov rax, r11 ; on remet r11 dans rax, on s'était servit de rax pour les resultat des fonction
    jmp .loop_plus    

.case_diff_sign:
    call big_number_cmp
    cmp rax, 0
    je .case_equal
    jl .case_less
    jg .case_greater    

.case_equal:
    mov rdi, 4
    call allocateBigNumber
    jmp .done

.case_less:        
    mov r12, qword [rsi + 8]
    mov qword [r11 + 8], r12
    mov rbx, rsi ;INVERSER o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o
    mov rcx, rdi
    mov rax, r11 ; on remet r11 dans rax, on s'était servit de rax pour les resultat des fonction
    jmp .loop_minus

.case_greater:
    mov r12, qword [rdi + 8]
    mov qword [r11 + 8], r12
    mov rbx, rdi
    mov rcx, rsi
    mov rax, r11 ; on remet r11 dans rax, on s'était servit de rax pour les resultat des fonction
    jmp .loop_minus

.loop_plus:
   
    cmp r10, qword [rax]  ; Check if index reaches the capacity
    jg .end_loop_plus
    
    ; Add the corresponding digits of the big numbers
    cmp r10, qword [rbx + 8]
    jge .skip_first_plus
    mov r11, qword [rbx + (r10 + 3)*8]  ; Get digit of the first big number
    .skip_first_plus:
    cmp r10, qword [rcx + 8]
    jge .skip_second_plus
    add r11, qword [rcx + (r10 + 3)*8]  ; Add digit of the second big number
    .skip_second_plus:
    add r11, r9  ; Add carry
    mov qword [rax + (r10 + 3)*8 + 16], r11  ; Store the sum
    ; Update carry
    mov r9, 0  ; Reset carry
    cmp r11, 0x10000000  ; Check if the sum exceeds 2^60 (carry is generated)
    jl .next_plus
    mov r9, 1  ; Set carry
    sub r11, 0x10000000  ; Adjust sum
    

.next_plus:
    ; Increment index and continue loop
    inc r10
    jmp .loop_plus
    
.end_loop_plus:
    ; Set the size of the result
    mov r12, r10
    sub r12, 3
    mov qword [rax + 8], r12
    jmp .done

.loop_minus:
    
    cmp r10, rdx  ; Check if index reaches the capacity
    je .end_loop_minus
    
    cmp r10, qword [rbx + 8]
    jge .skip_first_sub
    mov r11, [rbx + (r10 + 3)*8 + 16]  ; Get digit of the first big number
    .skip_first_sub:
    cmp r10, qword [rcx + 8]
    jge .skip_second_sub
    sub r11, [rcx + (r10 + 3)*8 + 16]  ; Add digit of the second big number
    .skip_second_sub:
    sub r11, r9  ; sub carry
    mov qword [rax + (r10 + 3)*8 + 16], r11  ; Store the sum
    mov r9, 0  ; Reset borrow
    cmp r11, 0  ; Check if borrow is needed
    jge .next_minus
    mov r9, 1  ; Set borrow

.next_minus:
    ; Increment index and continue loop
    inc r10
    jmp .loop_minus

.end_loop_minus:
    ; Set the size of the result
    mov r12, r10
    sub r12, 3
    mov [rax + 8], r12
    jmp .done
    
.done: ;Return pointer to the result
    pop rbp
    ret


    
print_big_number_decimal:
    ; Arguments:
    ; rdi: Pointer to the big number array
    push rbp
    ; Allocate memory for the decimal representation
    mov rdx, qword [rdi + 8]        ; Size of the big number (read size from second element)
    shl rdx, 3                      ; Multiply by 8 to get size in bytes (each element is 8 bytes)
    add rdx, 1                      ; Add space for the null terminator
    call malloc                     ; Allocate memory
    mov rbx, rax                    ; Save pointer to the allocated memory

    ; Initialize variables for conversion
    mov rcx, 0                      ; Initialize index
    xor rax, rax                    ; Clear RAX for division operation

.convert_loop:
    cmp rcx, qword [rdi + 8]        ; Compare index with size
    jge .end_convert_loop           ; If index >= size, exit loop

    ; Get the current digit (element of the array)
    mov rdx, [rdi + rcx*8 + 16]     ; Load the 64-bit integer digit (starting from offset 16)
    
    ; Convert the digit to decimal
    mov r8, rdx                     ; Copy the digit to R8 for operations
    mov r9, 0                       ; Clear R9 for operations
    mov r10, 10                     ; Set R10 to 10 (for decimal conversion)

    .decimal_conversion_loop:
        div r10                      ; Divide RDX:RAX by R10, remainder in RDX, quotient in RAX
        add rdx, '0'                ; Convert remainder to ASCII digit
        push rdx                    ; Push the ASCII digit onto the stack
        mov rdx, rax                ; Move the quotient back to RDX for next division
        test rdx, rdx               ; Check if quotient is zero
        jnz .decimal_conversion_loop ; If not zero, continue conversion

    ; Pop digits from stack to the allocated memory (in reverse order)
    .pop_digits_loop:
        pop rax                     ; Pop ASCII digit from stack
        mov [rbx + rcx], al         ; Store ASCII digit in memory
        inc rcx                     ; Increment index
        cmp rcx, rdx                ; Compare index with number of digits
        jl .pop_digits_loop         ; If not all digits popped, continue loop

    jmp .next_digit                ; Continue with next digit in the big number

    .next_digit:
        inc rcx                     ; Increment index for the next digit
        jmp .convert_loop           ; Continue with next digit in the big number

    .end_convert_loop:
    mov byte [rbx + rcx], 0         ; Null-terminate the string

    ; Call printf to print the decimal representation
    mov rdi, format                 ; Format string for printf
    mov rsi, rbx                    ; Pointer to the decimal string
    call printf

    ; Free the allocated memory
    mov rdi, rbx                    ; Pointer to the memory block
    call free
    pop rbp
    ret
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
%s""" % (toASMVariable(variableSet), toASMBSS(bigVariableSet, arraySet), getOpening(), toASMMainVariable(tree.children[0]), toASMCommand(tree.children[1]), toASMReturn(tree.children[2]), getClosing())

def countVariables(tree):
    variableSet = set()
    arraySet = set()
    bigVariableSet = set()
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
                elif child.data == "big_asgt":
                    bigVariableSet.add(child.children[0].value)

                countRec(child)
                
    countRec(tree)
    return variableSet, bigVariableSet, arraySet


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
        return BigNumberRepresentationToASM(tree.children[0].value, 28)
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


def BigNumberToSize(n, base):
    return math.floor(math.log(n) / math.log(base)) + 1

def BigNumberToRepresentation(n, base):
    digits = []
    value = n
    while value :
        digits.append(value % base)
        value //= base
    return digits

def BigNumberRepresentationToASM(n, base):
    global counter
    counter += 1
    digits = BigNumberToRepresentation(n , base)
    size = BigNumberToSize(n, base)
    res = f"""mov rdi, {size}
add rdi, 3
call allocateBigNumber
"""
    #f"""cmp [{tree.children[0].children[0].value}_capacity], {size}
    #jge no_init_{counter}:
    #mov rdi, {size + 3}
    #call allocateBigNumber
    #mov {var_name}_pointer, rax
    #.no_init_{counter}:
    #mov qword [{var_name}_pointer + 16], {size}
    #"""
    for i, digit in enumerate(digits):
        res += (f"\n mov qword [rax + {16 + i * 8}], {digit}")
    return res

def toASMCommand(tree):
    global counter
    if tree.data == "com_sequence":
        return "\n".join([toASMCommand(child) for child in tree.children])
    #SIZE, CAPACITY, ADRESSE (malloc)
    elif tree.data == "com_asgt":
        print("test", tree)
        print("test", tree.children[1])
        print("test", tree.children[0])
        #return BigNumberRepresentationToASM(int(tree.children[1].children[0].value), 28, tree.children[0].value)
        return f"""{toASMExpression(tree.children[1])}
mov rdi, {tree.children[0].value}
mov rsi, rax
call movBig
mov [{tree.children[0].value}], rax
"""
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


def toASMData(variableSet):
    res = ""    
    if not variableSet == set():
        res += "\n".join(["%s_size dq 0" % name for name in variableSet])
        res += "\n"
        res += "\n".join(["%s_capacity dq 0" % name for name in variableSet])
        res += "\n"
    return res

def toASMVariable(variableSet):
    res = ""
    if not variableSet == set():
        res +=  "\n".join(["%s: dq 0" % name for name in variableSet])
        res += "\n"
    return res

def toASMBSS(variableSet, arraySet):
    res = ""    
    if not variableSet == set():
        res += "\n".join(["%s_pointer resq 1" % name for name in variableSet])
        res += "\n"
    if not arraySet == set():
        res += "\n".join(["%s_size resq 1" % name for name in arraySet])
        res += "\n"
        res += "\n".join(["%s_pointer resq 1" % name for name in arraySet])
        res += "\n"
    return res
    
def toASMMainVariable(tree):
    # TODO GESTION DECOMPOSITION
    res = ""
    for i in range(len(tree.children)):
        res += """mov rbx, [argv]
    mov rdi, [rbx + %d]
    xor rax, rax
    call atoi
    mov [%s], rax
    """ % (8 * (i + 1), tree.children[i].value)
    return res

def save(filename, asm):
    with open(filename, "w") as file:
        file.write(asm)

print(tree3)
save("array.asm", toASM(tree2))
