package re.anas.cppcheck;

import java.io.*;
import java.nio.file.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.*;
import javax.swing.SwingUtilities;
import org.openide.modules.ModuleInstall;
import org.openide.modules.ModuleInfo;
import org.openide.util.Lookup;
import org.openide.util.lookup.Lookups;
import org.netbeans.api.project.Project;
import org.netbeans.api.project.ProjectManager;
import org.netbeans.spi.project.ActionProvider;
import org.netbeans.spi.project.ActionProgress;
import org.openide.filesystems.FileUtil;
import org.openide.loaders.DataObject;
import org.openide.cookies.EditorCookie;
import org.netbeans.api.autoupdate.*;

/** Integration checks inside the real NetBeans module system, never shipped. */
public final class Probe extends ModuleInstall {
    public void restored() {
        new Thread(() -> {
            int code = 1;
            try {
                if (System.getProperty("cpp.catalog") != null) install(); else check();
                code = 0;
            }
            catch (Throwable t) {
                t.printStackTrace();
                try (PrintStream error = new PrintStream(new FileOutputStream("verification/probe-error.txt"))) { t.printStackTrace(error); }
                catch (IOException ignored) {}
            }
            finally { System.exit(code); }
        }, "cpp-integration-check").start();
    }

    static void install() throws Exception {
        UpdateUnitProviderFactory factory = UpdateUnitProviderFactory.getDefault();
        for (UpdateUnitProvider p : factory.getUpdateUnitProviders(false)) p.setEnable(false);
        UpdateUnitProvider provider = factory.create("cpp-test", "C++ test catalog", new java.net.URI(System.getProperty("cpp.catalog")).toURL());
        provider.refresh(null, true);
        OperationContainer<InstallSupport> container = OperationContainer.createForInstall();
        for (UpdateUnit unit : UpdateManager.getDefault().getUpdateUnits(UpdateManager.TYPE.MODULE))
            if (unit.getCodeName().equals("re.anas.netbeans.cpp")) container.add(unit.getAvailableUpdates().get(0));
        if (container.listAll().isEmpty()) throw new AssertionError("Feature absent from catalog");
        int previous;
        do {
            previous = container.listAll().size();
            for (OperationContainer.OperationInfo<InstallSupport> i : new ArrayList<>(container.listAll()))
                container.add(i.getRequiredElements());
        } while (container.listAll().size() != previous);
        for (OperationContainer.OperationInfo<InstallSupport> i : container.listAll())
            if (!i.getBrokenDependencies().isEmpty()) throw new AssertionError(i.getUpdateElement() + ": " + i.getBrokenDependencies());
        if (!container.listInvalid().isEmpty()) throw new AssertionError("Invalid installation elements");
        System.out.println("Installing feature plus " + container.listAll().size() + " resolved modules");
        InstallSupport support = container.getSupport();
        InstallSupport.Validator validator = support.doDownload(null, false, true);
        InstallSupport.Installer installer = support.doValidate(validator, null);
        OperationSupport.Restarter restart = support.doInstall(installer, null);
        if (restart != null) support.doRestartLater(restart);
        System.out.println("PASS: Plugin Manager resolves and installs feature dependencies");
    }

    static ModuleInfo module(String name) {
        for (ModuleInfo m : Lookup.getDefault().lookupAll(ModuleInfo.class))
            if (m.getCodeNameBase().equals(name)) {
                if (!m.isEnabled()) throw new AssertionError("Disabled module: " + name);
                return m;
            }
        throw new AssertionError("Missing module: " + name);
    }
    static Class<?> cls(String mod, String name) throws Exception {
        return module(mod).getClassLoader().loadClass(name);
    }
    static void check() throws Exception {
        for (String n : new String[]{"cnd.kit", "cnd.editor", "cnd.makeproject", "cnd.makeproject.ui", "cnd.lsp", "cnd.toolchain", "cnd.debugger.gdb2"})
            module("org.netbeans.modules." + n);
        System.out.println("PASS: CND modules enabled");
        // Exercise loading of the LSP implementation, including its bundled libraries.
        cls("org.netbeans.modules.cnd.lsp", "org.netbeans.modules.cnd.lsp.server.ClangdProcess");
        Class<?> envClass = cls("org.netbeans.modules.dlight.nativeexecution", "org.netbeans.modules.nativeexecution.api.ExecutionEnvironment");
        Class<?> factory = cls("org.netbeans.modules.dlight.nativeexecution", "org.netbeans.modules.nativeexecution.api.ExecutionEnvironmentFactory");
        Object env = factory.getMethod("getLocal").invoke(null);
        System.out.println("PASS: native execution and LSP classes load");

        Path dir = Paths.get(System.getProperty("cpp.fixture")).toAbsolutePath();
        Files.createDirectories(dir);
        Path src = dir.resolve("main.cpp");
        Files.writeString(src, "#include <iostream>\nint main() { std::cout << \"CPP_PLUGIN_OK\" << std::endl; }\n");
        Files.writeString(dir.resolve("Makefile"), "all: app\napp: main.cpp\n\tg++ -g main.cpp -o app\nclean:\n\trm -f app\n");
        Class<?> configClass = cls("org.netbeans.modules.cnd.makeproject", "org.netbeans.modules.cnd.makeproject.api.configurations.MakeConfiguration");
        Object config = configClass.getMethod("createDefaultHostMakefileConfiguration", String.class, String.class).invoke(null, dir.toString(), "Debug");
        Class<?> gen = cls("org.netbeans.modules.cnd.makeproject", "org.netbeans.modules.cnd.makeproject.api.wizards.ProjectGenerator");
        Class<?> params = cls("org.netbeans.modules.cnd.makeproject", "org.netbeans.modules.cnd.makeproject.api.wizards.ProjectGenerator$ProjectParameters");
        Object p = params.getConstructor(String.class, File.class).newInstance("CppSmoke", dir.toFile());
        params.getMethod("setConfiguration", configClass).invoke(p, config);
        Project project = (Project)gen.getMethod("createProject", params).invoke(gen.getMethod("getDefault").invoke(null), p);
        if (project == null) throw new AssertionError("Project creation returned null");
        ProjectManager.getDefault().saveProject(project);
        System.out.println("PASS: C/C++ project creation and persistence");

        FileUtil.refreshFor(src.toFile());
        EditorCookie editor = DataObject.find(FileUtil.toFileObject(src.toFile())).getLookup().lookup(EditorCookie.class);
        if (editor == null) throw new AssertionError("No C++ editor");
        javax.swing.text.StyledDocument doc = editor.openDocument();
        doc.insertString(doc.getLength(), "// edited through NetBeans\n", null);
        editor.saveDocument();
        if (!Files.readString(src).contains("edited through NetBeans")) throw new AssertionError("Editor did not save");
        System.out.println("PASS: C++ editor open, edit and save");

        ActionProvider ap = project.getLookup().lookup(ActionProvider.class);
        if (ap == null) throw new AssertionError("No project build actions");
        CountDownLatch done = new CountDownLatch(1);
        boolean[] success = {false};
        ActionProgress progress = new ActionProgress() {
            protected void started() {}
            public void finished(boolean ok) { success[0] = ok; done.countDown(); }
        };
        SwingUtilities.invokeAndWait(() -> ap.invokeAction(ActionProvider.COMMAND_BUILD, Lookups.fixed(project, progress)));
        if (!done.await(150, TimeUnit.SECONDS) || !success[0]) throw new AssertionError("IDE Build failed or timed out");
        if (!Files.isExecutable(dir.resolve("app"))) throw new AssertionError("Build produced no executable");
        System.out.println("PASS: IDE Build action compiles C++ with g++");

        Class<?> builder = cls("org.netbeans.modules.dlight.nativeexecution", "org.netbeans.modules.nativeexecution.api.NativeProcessBuilder");
        Object b = builder.getMethod("newProcessBuilder", envClass).invoke(null, env);
        builder.getMethod("setExecutable", String.class).invoke(b, dir.resolve("app").toString());
        Process process = (Process)builder.getMethod("call").invoke(b);
        String output = new String(process.getInputStream().readAllBytes());
        if (process.waitFor() != 0 || !output.contains("CPP_PLUGIN_OK")) throw new AssertionError("Native run failed: " + output);
        System.out.println("PASS: native execution runs compiled C++ program");
        Files.writeString(Paths.get(System.getProperty("cpp.report")), "NetBeans 31: modules, project creation, editor, IDE Build, native execution PASS\n");
    }
}
