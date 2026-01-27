import UpCards from "./UpCards";
import CodeIcon from '@mui/icons-material/Code';
import GroupsIcon from '@mui/icons-material/Groups';
import ChatIcon from '@mui/icons-material/Chat';
import AssistantIcon from '@mui/icons-material/Assistant';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import LiveHelpIcon from '@mui/icons-material/LiveHelp';

function Page() {
  return (
    <div className="bg-white dark:bg-[#1B1E19]">
      <div className="w-screen flex justify-center md:justify-around pt-9 mb-7 px-4 bg-gray-100 dark:bg-[#1B1E19] transition-colors duration-300">
        <div className="flex flex-col md:flex-row md:gap-6 items-center justify-between max-w-screen-xl w-full py-9">
          {/* Left Section */}
          <div className="w-full md:w-1/2 text-left ml-5">
            <h2 className="text-3xl font-bold mb-5 md:py-2 lg:mb-6 text-gray-800 dark:text-white mt-5 md:mt-0">
              Build. Collaborate. Ship
              <p>in Real Time</p>
            </h2>

            <div className=" text-gray-700 dark:text-[#e0e0e0] font-medium">
              <div className="text-gray-700 dark:text-[#e0e0e0] font-medium text-base md:text-lg leading-relaxed max-w-xl">
                {/* Small screens */}
                <p className="block lg:hidden">
                  Code live, debug together, talk instantly, chat together, organise meetings and let AI handle the heavy lifting. Build faster, together.
                </p>

                {/* Medium and larger screens */}
                <div className="hidden lg:block space-y-3">
                  <p>Building software shouldn’t feel disconnected. Ideas move fast — your tools should too.Collabryx keeps everyone in the same moment. No waiting. No silos. No broken flow.</p>
                  <p>Just your team, thinking and building together. From the first idea to the final commit — in sync.Work feels lighter when collaboration feels natural. This is how modern teams build.</p>
                  <p>Welcome to Collabryx.</p>
                </div>
              </div>
              <br />
              <a className="cursor-pointer text-blue-600 hover:underline">
                Login
              </a>{" "}
              if you are already a registered user.
            </div>
          </div>

          {/* Right Section */}
          <div className="w-full md:w-1/2 p-5 ml-3">
            <img
              src="logocollabryx.png"
              alt="Video Conference Illustration"
              className="w-full h-auto object-contain rounded-lg"
            />
          </div>
        </div>
      </div>

      <div className="w-screen flex justify-center md:justify-around  mx-auto bg-white dark:bg-[#181C14]">
        <div className="text-black dark:text-white mt-8 md:mt-16 max-w-screen-xl mb-11">
          <div>
            <p className="flex justify-center items-center text-3xl font-bold">Why Choose Collabryx</p>
            <p className="flex justify-center items-center text-3xl font-bold"></p>
          </div>
          <div className="grid md:grid-cols-3 grid-cols-2 gap-x-[2rem] lg:gap-x-[9rem] xl:gap-x-[13rem] md:gap-x-[3rem] gap-y-15 mx-6 py-5 mt-4">
            <UpCards
              icon={<CodeIcon style={{ color: "#0f57e9" }} />}
              bgColor="#cfdeff"
              title={["Code", "together"]}
              description="Write, edit, and review code live with your team in one shared workspace."
            />
            <UpCards
              icon={<GroupsIcon style={{ color: "#f4986c" }} />}
              bgColor="#f3e2de"
              title={["Meet while", "you build"]}
              description="Start video meetings instantly and discuss ideas as you work."
            />
            <UpCards
              icon={<ChatIcon style={{ color: "#f9cb44" }} />}
              bgColor="#fff4d8"
              title={["Chat in", "real time"]}
              description="Share updates, ask questions, and stay connected during your sessions."
            />
            <UpCards
              icon={<AssistantIcon style={{ color: "#7b61ff" }} />}
              bgColor="#ece8ff"
              title={["Smart AI", "assistant"]}
              description="Ask questions and get clear answers from your company’s documents."
            />
            <UpCards
              icon={<CloudUploadIcon style={{ color: "#2fbf71" }} />}
              bgColor="#e4f7ee"
              title={["Learns from", "new files"]}
              description="Upload new documents once and let the AI use them anytime instantly."
            />
            <UpCards
              icon={<LiveHelpIcon style={{ color: "#ff6b6b" }} />}
              bgColor="#fdecec"
              title={["AI help", "inside code"]}
              description="Get live code suggestions and quick fixes as you type."
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default Page;