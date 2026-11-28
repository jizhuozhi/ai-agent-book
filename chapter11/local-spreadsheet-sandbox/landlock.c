#define _GNU_SOURCE
#include <fcntl.h>
#include <linux/landlock.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

static void fail(const char *operation)
{
    perror(operation);
    exit(EXIT_FAILURE);
}

static void allow_path(int ruleset, const char *path, unsigned long long rights)
{
    int fd = open(path, O_PATH | O_CLOEXEC);
    if (fd < 0)
        fail(path);
    struct stat info;
    if (fstat(fd, &info) < 0)
        fail("fstat");
    if (!S_ISDIR(info.st_mode))
        rights &= LANDLOCK_ACCESS_FS_READ_FILE | LANDLOCK_ACCESS_FS_EXECUTE;

    struct landlock_path_beneath_attr rule = {
        .allowed_access = rights,
        .parent_fd = fd,
    };
    if (syscall(SYS_landlock_add_rule, ruleset, LANDLOCK_RULE_PATH_BENEATH,
                &rule, 0) < 0)
        fail(path);
    close(fd);
}

int main(int argc, char **argv)
{
    if (argc != 5) {
        fputs("Usage: landlock INPUT WORKER OUTPUT_DIR PORT\n", stderr);
        return EXIT_FAILURE;
    }
    int abi = syscall(SYS_landlock_create_ruleset, NULL, 0,
                      LANDLOCK_CREATE_RULESET_VERSION);
    if (abi < 0)
        fail("query Landlock ABI");
    if (abi < 4) {
        fprintf(stderr, "The lab needs Landlock ABI 4 or later, found %d\n", abi);
        return EXIT_FAILURE;
    }

    const unsigned long long read = LANDLOCK_ACCESS_FS_READ_FILE |
                                    LANDLOCK_ACCESS_FS_READ_DIR;
    const unsigned long long write = LANDLOCK_ACCESS_FS_WRITE_FILE |
                                     LANDLOCK_ACCESS_FS_TRUNCATE |
                                     LANDLOCK_ACCESS_FS_MAKE_REG;
    struct landlock_ruleset_attr rules = {
        .handled_access_fs = read | write | LANDLOCK_ACCESS_FS_EXECUTE |
                             LANDLOCK_ACCESS_FS_REMOVE_FILE | LANDLOCK_ACCESS_FS_REMOVE_DIR |
                             LANDLOCK_ACCESS_FS_MAKE_DIR | LANDLOCK_ACCESS_FS_MAKE_CHAR |
                             LANDLOCK_ACCESS_FS_MAKE_BLOCK | LANDLOCK_ACCESS_FS_MAKE_SOCK |
                             LANDLOCK_ACCESS_FS_MAKE_FIFO | LANDLOCK_ACCESS_FS_MAKE_SYM |
                             LANDLOCK_ACCESS_FS_REFER,
        .handled_access_net = LANDLOCK_ACCESS_NET_BIND_TCP | LANDLOCK_ACCESS_NET_CONNECT_TCP,
    };
    int ruleset = syscall(SYS_landlock_create_ruleset, &rules, sizeof(rules), 0);
    if (ruleset < 0)
        fail("create Landlock ruleset");
    const char *runtime[] = {"/usr", "/lib", "/lib64"};
    for (size_t i = 0; i < sizeof(runtime) / sizeof(runtime[0]); i++) {
        if (access(runtime[i], F_OK) == 0)
            allow_path(ruleset, runtime[i], read | LANDLOCK_ACCESS_FS_EXECUTE);
    }
    allow_path(ruleset, argv[1], read);
    allow_path(ruleset, argv[2], read);
    allow_path(ruleset, argv[3], read | write);

    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) < 0)
        fail("PR_SET_NO_NEW_PRIVS");
    if (syscall(SYS_landlock_restrict_self, ruleset, 0) < 0)
        fail("apply Landlock ruleset");
    close(ruleset);

    char *command[] = {"/usr/bin/python3", "-I", "-B", argv[2], argv[1],
                       argv[3], argv[4], NULL};
    execv(command[0], command);
    fail("exec python3");
}
