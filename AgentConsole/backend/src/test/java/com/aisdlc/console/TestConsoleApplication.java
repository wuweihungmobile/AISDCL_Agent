package com.aisdlc.console;

import org.springframework.boot.SpringApplication;

public class TestConsoleApplication {

	public static void main(String[] args) {
		SpringApplication.from(ConsoleApplication::main).with(TestcontainersConfiguration.class).run(args);
	}

}
