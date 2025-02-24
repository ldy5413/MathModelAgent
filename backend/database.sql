-- Active: 1733305978141@@127.0.0.1@3306
create Table book(
    id integer primary key AUTOINCREMENT,
    title varchar(255) not null,
    author varchar(255) not null
);

insert into book (title, author) values ('1984', 'George Orwell');
insert into book (title, author) values ('To Kill a Mockingbird', 'Harper Lee');
insert into book (title, author) values ('Pride and Prejudice', 'Jane Austen');


create table user(
    id integer primary key AUTOINCREMENT,
    account varchar(255) not null,
    password varchar(255) not null
);

create table token(
    id integer primary key AUTOINCREMENT,
    access_token varchar(255) not null,
    token_type varchar(255) not null,
    user_id integer not null,
    foreign key (user_id) references user(id)
);
