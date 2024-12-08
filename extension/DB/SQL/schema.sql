CREATE TABLE News (
                      Link VARCHAR PRIMARY KEY,
                      Title VARCHAR,
                      Content TEXT,
                      Source VARCHAR,
                      CollectDate DATE
);

CREATE TABLE Rated (
                       Link VARCHAR PRIMARY KEY,
                       Model VARCHAR,
                       Score INT,
                       Reason VARCHAR,
                       FOREIGN KEY (Link) REFERENCES News(Link)
);

CREATE TABLE Response (
                          id INT PRIMARY KEY,
                          Link VARCHAR,
                          Score INT,
                          Comments VARCHAR,
                          FOREIGN KEY (Link) REFERENCES News(Link)
);