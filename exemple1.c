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
